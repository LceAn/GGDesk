package main

import (
	"database/sql"
	"encoding/json"
	"errors"
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
	"strings"
	"time"
)

type OutputShortcut struct {
	Name   string `json:"name"`
	Target string `json:"target"`
	Path   string `json:"path"`
}

type GenerateReport struct {
	OutputPath string   `json:"outputPath"`
	Created    int      `json:"created"`
	Added      int      `json:"added"`
	Failures   []string `json:"failures"`
}

func (a *App) ResolveOutputPath(path string) string {
	path = strings.TrimSpace(path)
	if path == "" {
		return desktopDefaultOutputPath()
	}
	return filepath.Clean(path)
}

func (a *App) SaveOutputPath(path string) error {
	bundle, err := a.GetSettingsBundle()
	if err != nil {
		return err
	}
	bundle.Settings["output_path"] = strings.TrimSpace(path)
	return a.SaveSettingsBundle(bundle)
}

func (a *App) PreviewOutputShortcuts(path string) ([]OutputShortcut, error) {
	resolved := a.ResolveOutputPath(path)
	if _, err := os.Stat(resolved); os.IsNotExist(err) {
		return []OutputShortcut{}, nil
	}
	if runtime.GOOS == "windows" {
		return previewWindowsShortcuts(resolved)
	}
	entries, err := os.ReadDir(resolved)
	if err != nil {
		return nil, err
	}
	items := []OutputShortcut{}
	for _, entry := range entries {
		if !entry.IsDir() {
			items = append(items, OutputShortcut{Name: entry.Name(), Target: filepath.Join(resolved, entry.Name()), Path: filepath.Join(resolved, entry.Name())})
		}
	}
	return items, nil
}

func (a *App) GenerateShortcutsFromScan(results []ScanResult, outputPath string, addToDB bool) (GenerateReport, error) {
	if err := a.ensureDB(); err != nil {
		return GenerateReport{}, err
	}
	out := a.ResolveOutputPath(outputPath)
	if err := os.MkdirAll(out, 0755); err != nil {
		return GenerateReport{}, err
	}
	report := GenerateReport{OutputPath: out, Failures: []string{}}
	for _, result := range results {
		if !result.Selected {
			continue
		}
		name := strings.TrimSpace(result.Name)
		if name == "" {
			name = strings.TrimSuffix(filepath.Base(result.ExePath), filepath.Ext(result.ExePath))
		}
		lnkPath := filepath.Join(out, sanitizeFilename(name)+".lnk")
		args := uwpArgs(result)
		if err := createShortcutFile(result.ExePath, lnkPath, args); err != nil {
			report.Failures = append(report.Failures, name+": "+err.Error())
			continue
		}
		report.Created++
		if addToDB {
			result.LnkPath = lnkPath
			if result.Category == "" {
				result.Category = SuggestCategory(result.Name, result.ExePath, result.SourceType)
			}
			if err := a.upsertShortcut(result); err != nil {
				report.Failures = append(report.Failures, name+" 入库失败: "+err.Error())
			} else {
				report.Added++
			}
		}
	}
	return report, nil
}

func (a *App) upsertShortcut(result ScanResult) error {
	category := cleanCategory(result.Category)
	if category == "" {
		category = SuggestCategory(result.Name, result.ExePath, result.SourceType)
	}
	tx, err := a.db.Begin()
	if err != nil {
		return err
	}
	defer tx.Rollback()
	if _, err := tx.Exec(`INSERT OR IGNORE INTO categories (name) VALUES (?)`, category); err != nil {
		return err
	}
	var id int64
	err = tx.QueryRow(`SELECT id FROM shortcuts WHERE exe_path = ?`, result.ExePath).Scan(&id)
	if err == sql.ErrNoRows {
		_, err = tx.Exec(`INSERT INTO shortcuts (name, exe_path, lnk_path, source_type, args, category, added_at)
			VALUES (?, ?, ?, ?, ?, ?, ?)`, result.Name, result.ExePath, result.LnkPath, result.SourceType, uwpArgs(result), category, time.Now().Format(time.RFC3339))
	} else if err == nil {
		_, err = tx.Exec(`UPDATE shortcuts SET name = ?, lnk_path = ?, source_type = ?, args = ?, category = ? WHERE id = ?`,
			result.Name, result.LnkPath, result.SourceType, uwpArgs(result), category, id)
	}
	if err != nil {
		return err
	}
	return tx.Commit()
}

func previewWindowsShortcuts(path string) ([]OutputShortcut, error) {
	script := `
$ErrorActionPreference = "Stop"
$shell = New-Object -ComObject WScript.Shell
$items = @()
Get-ChildItem -LiteralPath $env:GGDESK_LNK_DIR -Filter *.lnk -File | ForEach-Object {
  try {
    $shortcut = $shell.CreateShortcut($_.FullName)
    $items += [PSCustomObject]@{ name = $_.Name; target = $shortcut.TargetPath; path = $_.FullName }
  } catch {
    $items += [PSCustomObject]@{ name = $_.Name; target = "无法读取目标"; path = $_.FullName }
  }
}
$items | ConvertTo-Json -Compress
`
	cmd := exec.Command("powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script)
	cmd.Env = append(os.Environ(), "GGDESK_LNK_DIR="+path)
	out, err := cmd.Output()
	if err != nil {
		return nil, err
	}
	text := strings.TrimSpace(string(out))
	if text == "" {
		return []OutputShortcut{}, nil
	}
	items := []OutputShortcut{}
	if err := json.Unmarshal([]byte(text), &items); err != nil {
		var one OutputShortcut
		if err2 := json.Unmarshal([]byte(text), &one); err2 == nil && one.Name != "" {
			return []OutputShortcut{one}, nil
		}
		return nil, err
	}
	return items, nil
}

func createShortcutFile(targetPath, shortcutPath, args string) error {
	if runtime.GOOS != "windows" {
		return errors.New("当前只支持在 Windows 生成 .lnk 快捷方式")
	}
	if strings.TrimSpace(targetPath) == "" {
		return errors.New("目标路径为空")
	}
	if err := os.MkdirAll(filepath.Dir(shortcutPath), 0755); err != nil {
		return err
	}
	script := `
$ErrorActionPreference = "Stop"
$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($env:GGDESK_LNK_PATH)
if ($env:GGDESK_LNK_ARGS -ne "") {
  $shortcut.TargetPath = "explorer.exe"
  $shortcut.Arguments = $env:GGDESK_LNK_ARGS
  $shortcut.IconLocation = "explorer.exe,0"
} else {
  $shortcut.TargetPath = $env:GGDESK_LNK_TARGET
  if (Test-Path -LiteralPath $env:GGDESK_LNK_TARGET) {
    $shortcut.WorkingDirectory = Split-Path -Parent $env:GGDESK_LNK_TARGET
    $shortcut.IconLocation = $env:GGDESK_LNK_TARGET
  }
}
$shortcut.Save()
`
	cmd := exec.Command("powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script)
	cmd.Env = append(os.Environ(),
		"GGDESK_LNK_TARGET="+targetPath,
		"GGDESK_LNK_PATH="+shortcutPath,
		"GGDESK_LNK_ARGS="+args,
	)
	if out, err := cmd.CombinedOutput(); err != nil {
		return errors.New(strings.TrimSpace(string(out)) + " " + err.Error())
	}
	return nil
}

func sanitizeFilename(value string) string {
	value = strings.TrimSpace(value)
	replacer := strings.NewReplacer("\\", "_", "/", "_", ":", "_", "*", "_", "?", "_", "\"", "_", "<", "_", ">", "_", "|", "_")
	value = replacer.Replace(value)
	if value == "" {
		return "shortcut"
	}
	return value
}
