package main

import (
	"context"
	"database/sql"
	"errors"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
	"sort"
	"strings"
	"sync"
	"time"

	_ "modernc.org/sqlite"
)

const defaultCategory = "默认"

type App struct {
	ctx    context.Context
	db     *sql.DB
	dbPath string
	mu     sync.Mutex
}

type Overview struct {
	DBPath      string   `json:"dbPath"`
	Total       int      `json:"total"`
	Categories  []string `json:"categories"`
	Accent      string   `json:"accent"`
	RuntimeNote string   `json:"runtimeNote"`
}

type Shortcut struct {
	ID         int64  `json:"id"`
	Name       string `json:"name"`
	ExePath    string `json:"exePath"`
	LnkPath    string `json:"lnkPath"`
	Args       string `json:"args"`
	SourceType string `json:"sourceType"`
	Category   string `json:"category"`
	RunCount   int    `json:"runCount"`
	AddedAt    string `json:"addedAt"`
}

type ShortcutFilter struct {
	Category string `json:"category"`
	Query    string `json:"query"`
	SortBy   string `json:"sortBy"`
}

type ScanOptions struct {
	CustomPath       string `json:"customPath"`
	IncludeStartMenu bool   `json:"includeStartMenu"`
	Limit            int    `json:"limit"`
}

type ScanResult struct {
	Name       string `json:"name"`
	ExePath    string `json:"exePath"`
	LnkPath    string `json:"lnkPath"`
	SourceType string `json:"sourceType"`
	RootPath   string `json:"rootPath"`
	Category   string `json:"category"`
	Status     string `json:"status"`
	Selected   bool   `json:"selected"`
}

func NewApp() *App {
	return &App{}
}

func (a *App) startup(ctx context.Context) {
	a.ctx = ctx
	if err := a.ensureDB(); err != nil {
		fmt.Println("database startup:", err)
	}
}

func (a *App) ensureDB() error {
	a.mu.Lock()
	defer a.mu.Unlock()
	if a.db != nil {
		return nil
	}

	dbPath, err := locateDatabase()
	if err != nil {
		return err
	}
	if err := os.MkdirAll(filepath.Dir(dbPath), 0755); err != nil {
		return err
	}

	db, err := sql.Open("sqlite", dbPath)
	if err != nil {
		return err
	}
	a.db = db
	a.dbPath = dbPath
	return a.initSchema()
}

func locateDatabase() (string, error) {
	return userDatabasePath(), nil
}

func (a *App) initSchema() error {
	queries := []string{
		`CREATE TABLE IF NOT EXISTS shortcuts (
			id INTEGER PRIMARY KEY AUTOINCREMENT,
			name TEXT NOT NULL,
			exe_path TEXT,
			lnk_path TEXT,
			args TEXT,
			icon_path TEXT,
			source_type TEXT,
			category TEXT DEFAULT '默认',
			run_count INTEGER DEFAULT 0,
			is_pinned BOOLEAN DEFAULT 0,
			added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
		)`,
		`CREATE TABLE IF NOT EXISTS categories (
			id INTEGER PRIMARY KEY AUTOINCREMENT,
			name TEXT UNIQUE NOT NULL,
			sort_order INTEGER DEFAULT 0
		)`,
	}
	for _, q := range queries {
		if _, err := a.db.Exec(q); err != nil {
			return err
		}
	}
	if err := a.ensureColumn("shortcuts", "category", "TEXT DEFAULT '默认'"); err != nil {
		return err
	}
	if _, err := a.db.Exec(`INSERT OR IGNORE INTO categories (name, sort_order) VALUES (?, ?)`, defaultCategory, 0); err != nil {
		return err
	}
	if _, err := a.db.Exec(`UPDATE shortcuts SET category = ? WHERE category IS NULL OR TRIM(category) = ''`, defaultCategory); err != nil {
		return err
	}
	return a.backfillCategories()
}

func (a *App) ensureColumn(table, name, definition string) error {
	rows, err := a.db.Query("PRAGMA table_info(" + table + ")")
	if err != nil {
		return err
	}
	defer rows.Close()
	for rows.Next() {
		var cid int
		var colName, colType string
		var notNull, pk int
		var defaultValue any
		if err := rows.Scan(&cid, &colName, &colType, &notNull, &defaultValue, &pk); err != nil {
			return err
		}
		if colName == name {
			return nil
		}
	}
	_, err = a.db.Exec(fmt.Sprintf("ALTER TABLE %s ADD COLUMN %s %s", table, name, definition))
	return err
}

func (a *App) backfillCategories() error {
	rows, err := a.db.Query(`SELECT DISTINCT category FROM shortcuts WHERE category IS NOT NULL AND TRIM(category) != ''`)
	if err != nil {
		return err
	}
	defer rows.Close()
	for rows.Next() {
		var name string
		if err := rows.Scan(&name); err != nil {
			return err
		}
		if _, err := a.db.Exec(`INSERT OR IGNORE INTO categories (name) VALUES (?)`, cleanCategory(name)); err != nil {
			return err
		}
	}
	return rows.Err()
}

func (a *App) GetOverview() (Overview, error) {
	if err := a.ensureDB(); err != nil {
		return Overview{}, err
	}
	var total int
	if err := a.db.QueryRow(`SELECT COUNT(*) FROM shortcuts`).Scan(&total); err != nil {
		return Overview{}, err
	}
	categories, err := a.GetCategories(false)
	if err != nil {
		return Overview{}, err
	}
	return Overview{
		DBPath:      a.dbPath,
		Total:       total,
		Categories:  categories,
		Accent:      "#1a73e8",
		RuntimeNote: "Go 后端 + Wails WebView，扫描和数据操作会逐步迁到后台任务。",
	}, nil
}

func (a *App) ListShortcuts(filter ShortcutFilter) ([]Shortcut, error) {
	if err := a.ensureDB(); err != nil {
		return nil, err
	}
	orderBy := "LOWER(name) ASC"
	switch filter.SortBy {
	case "count":
		orderBy = "run_count DESC, LOWER(name) ASC"
	case "added":
		orderBy = "added_at DESC"
	}

	query := strings.TrimSpace(filter.Query)
	category := strings.TrimSpace(filter.Category)
	args := []any{}
	where := []string{}
	if category != "" && category != "全部" {
		where = append(where, "category = ?")
		args = append(args, category)
	}
	if query != "" {
		like := "%" + strings.ToLower(query) + "%"
		where = append(where, "(LOWER(name) LIKE ? OR LOWER(COALESCE(exe_path, '')) LIKE ? OR LOWER(COALESCE(category, '')) LIKE ?)")
		args = append(args, like, like, like)
	}

	sqlText := `SELECT id, name, COALESCE(exe_path, ''), COALESCE(lnk_path, ''), COALESCE(args, ''),
		COALESCE(source_type, ''), COALESCE(category, '默认'), COALESCE(run_count, 0), COALESCE(added_at, '')
		FROM shortcuts`
	if len(where) > 0 {
		sqlText += " WHERE " + strings.Join(where, " AND ")
	}
	sqlText += " ORDER BY " + orderBy

	rows, err := a.db.Query(sqlText, args...)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	shortcuts := []Shortcut{}
	for rows.Next() {
		var s Shortcut
		if err := rows.Scan(&s.ID, &s.Name, &s.ExePath, &s.LnkPath, &s.Args, &s.SourceType, &s.Category, &s.RunCount, &s.AddedAt); err != nil {
			return nil, err
		}
		shortcuts = append(shortcuts, s)
	}
	return shortcuts, rows.Err()
}

func (a *App) GetCategories(includeAll bool) ([]string, error) {
	if err := a.ensureDB(); err != nil {
		return nil, err
	}
	rows, err := a.db.Query(`SELECT name FROM categories ORDER BY sort_order ASC, name COLLATE NOCASE ASC`)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	seen := map[string]bool{}
	names := []string{}
	for rows.Next() {
		var name string
		if err := rows.Scan(&name); err != nil {
			return nil, err
		}
		name = cleanCategory(name)
		if !seen[name] {
			names = append(names, name)
			seen[name] = true
		}
	}
	if !seen[defaultCategory] {
		names = append([]string{defaultCategory}, names...)
	}
	if includeAll {
		return append([]string{"全部"}, names...), nil
	}
	return names, nil
}

func (a *App) CreateCategory(name string) (string, error) {
	if err := a.ensureDB(); err != nil {
		return "", err
	}
	clean := cleanCategory(name)
	if clean == "" {
		return "", errors.New("分类名称不能为空")
	}
	_, err := a.db.Exec(`INSERT OR IGNORE INTO categories (name) VALUES (?)`, clean)
	return clean, err
}

func (a *App) RenameCategory(oldName, newName string) error {
	if err := a.ensureDB(); err != nil {
		return err
	}
	oldName = cleanCategory(oldName)
	newName = cleanCategory(newName)
	if oldName == "" || newName == "" {
		return errors.New("分类名称不能为空")
	}
	if oldName == defaultCategory {
		return errors.New("默认分类不能重命名")
	}
	tx, err := a.db.Begin()
	if err != nil {
		return err
	}
	defer tx.Rollback()
	if _, err := tx.Exec(`INSERT OR IGNORE INTO categories (name) VALUES (?)`, newName); err != nil {
		return err
	}
	if _, err := tx.Exec(`UPDATE shortcuts SET category = ? WHERE category = ?`, newName, oldName); err != nil {
		return err
	}
	if _, err := tx.Exec(`DELETE FROM categories WHERE name = ?`, oldName); err != nil {
		return err
	}
	return tx.Commit()
}

func (a *App) DeleteCategory(name string) error {
	if err := a.ensureDB(); err != nil {
		return err
	}
	name = cleanCategory(name)
	if name == "" {
		return errors.New("分类名称不能为空")
	}
	if name == defaultCategory {
		return errors.New("默认分类不能删除")
	}
	tx, err := a.db.Begin()
	if err != nil {
		return err
	}
	defer tx.Rollback()
	if _, err := tx.Exec(`UPDATE shortcuts SET category = ? WHERE category = ?`, defaultCategory, name); err != nil {
		return err
	}
	if _, err := tx.Exec(`DELETE FROM categories WHERE name = ?`, name); err != nil {
		return err
	}
	return tx.Commit()
}

func (a *App) UpdateShortcutCategory(id int64, category string) error {
	if err := a.ensureDB(); err != nil {
		return err
	}
	category = cleanCategory(category)
	if _, err := a.db.Exec(`INSERT OR IGNORE INTO categories (name) VALUES (?)`, category); err != nil {
		return err
	}
	_, err := a.db.Exec(`UPDATE shortcuts SET category = ? WHERE id = ?`, category, id)
	return err
}

func (a *App) DeleteShortcut(id int64) error {
	if err := a.ensureDB(); err != nil {
		return err
	}
	_, err := a.db.Exec(`DELETE FROM shortcuts WHERE id = ?`, id)
	return err
}

func (a *App) AutoClassify() (int, error) {
	if err := a.ensureDB(); err != nil {
		return 0, err
	}
	shortcuts, err := a.ListShortcuts(ShortcutFilter{SortBy: "added"})
	if err != nil {
		return 0, err
	}
	changed := 0
	for _, s := range shortcuts {
		next := SuggestCategory(s.Name, s.ExePath, s.SourceType)
		if next != "" && next != s.Category {
			if err := a.UpdateShortcutCategory(s.ID, next); err != nil {
				return changed, err
			}
			changed++
		}
	}
	return changed, nil
}

func (a *App) LaunchShortcut(id int64) error {
	if err := a.ensureDB(); err != nil {
		return err
	}
	s, err := a.getShortcut(id)
	if err != nil {
		return err
	}
	var cmd *exec.Cmd
	if runtime.GOOS == "windows" && s.SourceType == "uwp" && strings.TrimSpace(s.Args) != "" {
		cmd = exec.Command("explorer.exe", s.Args)
	} else {
		target := s.ExePath
		if strings.TrimSpace(target) == "" {
			target = s.LnkPath
		}
		if strings.TrimSpace(target) == "" {
			return errors.New("快捷方式路径为空")
		}
		if runtime.GOOS == "windows" {
			cmd = exec.Command("rundll32.exe", "url.dll,FileProtocolHandler", target)
		} else {
			cmd = exec.Command("open", target)
		}
	}
	if err := cmd.Start(); err != nil {
		return err
	}
	_, _ = a.db.Exec(`UPDATE shortcuts SET run_count = run_count + 1 WHERE id = ?`, id)
	return nil
}

func (a *App) OpenFileLocation(id int64) error {
	if err := a.ensureDB(); err != nil {
		return err
	}
	s, err := a.getShortcut(id)
	if err != nil {
		return err
	}
	target := s.ExePath
	if _, err := os.Stat(target); err != nil && s.LnkPath != "" {
		target = s.LnkPath
	}
	if target == "" {
		return errors.New("没有可打开的位置")
	}
	if runtime.GOOS == "windows" {
		return exec.Command("explorer.exe", "/select,"+target).Start()
	}
	return exec.Command("open", filepath.Dir(target)).Start()
}

func (a *App) getShortcut(id int64) (Shortcut, error) {
	var s Shortcut
	err := a.db.QueryRow(`SELECT id, name, COALESCE(exe_path, ''), COALESCE(lnk_path, ''), COALESCE(args, ''),
		COALESCE(source_type, ''), COALESCE(category, '默认'), COALESCE(run_count, 0), COALESCE(added_at, '')
		FROM shortcuts WHERE id = ?`, id).
		Scan(&s.ID, &s.Name, &s.ExePath, &s.LnkPath, &s.Args, &s.SourceType, &s.Category, &s.RunCount, &s.AddedAt)
	return s, err
}

func (a *App) ScanPrograms(options ScanOptions) ([]ScanResult, error) {
	if err := a.ensureDB(); err != nil {
		return nil, err
	}
	limit := options.Limit
	if limit <= 0 || limit > 1000 {
		limit = 300
	}

	existing, err := a.existingTargets()
	if err != nil {
		return nil, err
	}

	results := []ScanResult{}
	add := func(result ScanResult) {
		if len(results) >= limit {
			return
		}
		key := normalizeTarget(result.ExePath)
		if key == "" {
			key = normalizeTarget(result.LnkPath)
		}
		if existing[key] {
			result.Status = "已存在"
			result.Selected = false
		} else {
			result.Status = "新增"
			result.Selected = true
		}
		result.Category = SuggestCategory(result.Name, result.ExePath, result.SourceType)
		results = append(results, result)
	}

	if options.IncludeStartMenu {
		for _, root := range startMenuRoots() {
			_ = filepath.WalkDir(root, func(path string, d os.DirEntry, err error) error {
				if err != nil || len(results) >= limit {
					return nil
				}
				if d.IsDir() {
					return nil
				}
				if strings.EqualFold(filepath.Ext(path), ".lnk") {
					name := strings.TrimSuffix(filepath.Base(path), filepath.Ext(path))
					add(ScanResult{Name: name, ExePath: path, LnkPath: path, SourceType: "start_menu", RootPath: root})
				}
				return nil
			})
		}
	}

	custom := strings.TrimSpace(options.CustomPath)
	if custom != "" {
		_ = filepath.WalkDir(custom, func(path string, d os.DirEntry, err error) error {
			if err != nil || len(results) >= limit {
				return nil
			}
			name := strings.ToLower(d.Name())
			if d.IsDir() {
				if shouldSkipDir(name) && path != custom {
					return filepath.SkipDir
				}
				return nil
			}
			if !strings.EqualFold(filepath.Ext(path), ".exe") || shouldSkipExecutable(name) {
				return nil
			}
			add(ScanResult{
				Name:       strings.TrimSuffix(filepath.Base(path), filepath.Ext(path)),
				ExePath:    path,
				SourceType: "custom",
				RootPath:   custom,
			})
			return nil
		})
	}

	sort.SliceStable(results, func(i, j int) bool {
		if results[i].Status != results[j].Status {
			return results[i].Status == "新增"
		}
		return strings.ToLower(results[i].Name) < strings.ToLower(results[j].Name)
	})
	return results, nil
}

func (a *App) AddScanResults(results []ScanResult) (int, error) {
	if err := a.ensureDB(); err != nil {
		return 0, err
	}
	tx, err := a.db.Begin()
	if err != nil {
		return 0, err
	}
	defer tx.Rollback()

	count := 0
	for _, r := range results {
		if !r.Selected {
			continue
		}
		name := strings.TrimSpace(r.Name)
		if name == "" {
			name = strings.TrimSuffix(filepath.Base(r.ExePath), filepath.Ext(r.ExePath))
		}
		category := cleanCategory(r.Category)
		if category == "" {
			category = SuggestCategory(name, r.ExePath, r.SourceType)
		}
		if _, err := tx.Exec(`INSERT OR IGNORE INTO categories (name) VALUES (?)`, category); err != nil {
			return count, err
		}
		var id int64
		err := tx.QueryRow(`SELECT id FROM shortcuts WHERE exe_path = ?`, r.ExePath).Scan(&id)
		if err == sql.ErrNoRows {
			_, err = tx.Exec(`INSERT INTO shortcuts (name, exe_path, lnk_path, source_type, args, category, added_at)
				VALUES (?, ?, ?, ?, ?, ?, ?)`, name, r.ExePath, r.LnkPath, r.SourceType, r.Args(), category, time.Now().Format(time.RFC3339))
		} else if err == nil {
			_, err = tx.Exec(`UPDATE shortcuts SET name = ?, lnk_path = ?, source_type = ?, args = ?, category = ? WHERE id = ?`,
				name, r.LnkPath, r.SourceType, r.Args(), category, id)
		}
		if err != nil {
			return count, err
		}
		count++
	}
	return count, tx.Commit()
}

func (r ScanResult) Args() string {
	if r.SourceType == "uwp" && r.ExePath != "" && !looksLikeFilesystemPath(r.ExePath) {
		return "shell:AppsFolder\\" + r.ExePath
	}
	return ""
}

func (a *App) existingTargets() (map[string]bool, error) {
	rows, err := a.db.Query(`SELECT COALESCE(exe_path, ''), COALESCE(lnk_path, '') FROM shortcuts`)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	existing := map[string]bool{}
	for rows.Next() {
		var exe, lnk string
		if err := rows.Scan(&exe, &lnk); err != nil {
			return nil, err
		}
		if key := normalizeTarget(exe); key != "" {
			existing[key] = true
		}
		if key := normalizeTarget(lnk); key != "" {
			existing[key] = true
		}
	}
	return existing, rows.Err()
}

func startMenuRoots() []string {
	roots := []string{}
	programData := os.Getenv("ProgramData")
	if programData != "" {
		roots = append(roots, filepath.Join(programData, "Microsoft", "Windows", "Start Menu", "Programs"))
	}
	appData := os.Getenv("APPDATA")
	if appData != "" {
		roots = append(roots, filepath.Join(appData, "Microsoft", "Windows", "Start Menu", "Programs"))
	}
	return roots
}

func shouldSkipDir(name string) bool {
	skips := []string{".git", "node_modules", "__pycache__", "cache", "logs", "backup", "temp", "tmp", "driver", "runtime", "redist"}
	for _, skip := range skips {
		if name == skip || strings.Contains(name, skip) {
			return true
		}
	}
	return false
}

func shouldSkipExecutable(name string) bool {
	bad := []string{"uninstall", "unins", "setup", "install", "update", "crashpad", "helper", "service", "driver", "broker"}
	for _, word := range bad {
		if strings.Contains(name, word) {
			return true
		}
	}
	return false
}

func cleanCategory(name string) string {
	clean := strings.TrimSpace(name)
	if clean == "" {
		return defaultCategory
	}
	return clean
}

func normalizeTarget(value string) string {
	return strings.ToLower(strings.TrimSpace(filepath.Clean(value)))
}

func looksLikeFilesystemPath(value string) bool {
	value = strings.TrimSpace(value)
	return strings.Contains(value, ":\\") || strings.Contains(value, ":/") || strings.HasPrefix(value, "\\\\")
}

func SuggestCategory(name, exePath, sourceType string) string {
	text := strings.ToLower(name + " " + exePath + " " + sourceType)
	categories := []struct {
		name     string
		keywords []string
	}{
		{"开发", []string{"code", "cursor", "codex", "visual studio", "vscode", "goland", "pycharm", "webstorm", "datagrip", "idea", "intellij", "phpstorm", "clion", "terminal", "git", "node", "python", "go.exe", "docker"}},
		{"AI 工具", []string{"chatgpt", "openai", "copilot", "claude", "gemini", "comfyui", "stable diffusion"}},
		{"设计", []string{"figma", "photoshop", "illustrator", "paint", "画图", "sketch", "xd", "blender", "creator"}},
		{"游戏", []string{"steam", "epic", "xbox", "game", "gaming", "battle.net", "riot", "minecraft"}},
		{"办公", []string{"word", "excel", "powerpoint", "office", "outlook", "onenote", "pdf", "notion", "wps", "copilot"}},
		{"浏览器", []string{"chrome", "edge", "firefox", "browser", "arc", "brave", "opera"}},
		{"通讯", []string{"wechat", "weixin", "qq", "teams", "discord", "telegram", "slack", "zoom"}},
		{"媒体", []string{"player", "music", "video", "media", "clipchamp", "photos", "zune", "obs", "vlc", "spotify", "照片", "媒体"}},
		{"云盘", []string{"onedrive", "dropbox", "drive", "icloud", "synology", "网盘"}},
		{"安全", []string{"1password", "password", "defender", "security", "vpn", "authenticator"}},
		{"系统工具", []string{"cmd", "powershell", "control", "settings", "system", "disk", "cleanup", "管理", "配置", "诊断", "终端"}},
	}
	for _, category := range categories {
		for _, keyword := range category.keywords {
			if strings.Contains(text, keyword) {
				return category.name
			}
		}
	}
	return defaultCategory
}
