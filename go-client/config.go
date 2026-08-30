package main

import (
	"bufio"
	"os"
	"path/filepath"
	"sort"
	"strings"
)

type SettingsBundle struct {
	Settings map[string]string   `json:"settings"`
	Rules    map[string]string   `json:"rules"`
	Lists    map[string][]string `json:"lists"`
	Paths    map[string]string   `json:"paths"`
}

var defaultSettings = map[string]string{
	"last_scan_path":       "",
	"output_path":          "",
	"window_geometry":      "",
	"theme":                "light",
	"is_first_run":         "false",
	"launcher_icon_size":   "72",
	"launcher_show_badges": "true",
	"launcher_sort_by":     "name",
	"sidebar_collapsed":    "false",
}

var defaultRules = map[string]string{
	"enable_blacklist":       "true",
	"enable_ignored_dirs":    "true",
	"enable_size_filter":     "false",
	"min_kb":                 "50",
	"max_mb":                 "200",
	"enable_deduplication":   "true",
	"default_check_new":      "true",
	"default_check_existing": "false",
	"enable_smart_root":      "true",
	"enable_prog_filter":     "true",
	"enable_bad_path":        "true",
	"dedup_threshold":        "0.6",
}

var defaultLists = map[string][]string{
	"blocklist": {
		"uninstall.exe", "unins000.exe", "setup.exe", "install.exe", "update.exe",
		"launcherhelper.exe", "crashpad_handler.exe", "vcredist.exe",
	},
	"ignored_dirs": {
		".git", "node_modules", "__pycache__", "cache", "logs", "backup", "temp", "tmp",
		"driver", "drivers", "runtime", "redist",
	},
	"prog_runtimes": {
		"python.exe", "pythonw.exe", "node.exe", "java.exe", "go.exe", "dotnet.exe",
	},
	"bad_path_keywords": {
		"uninstall", "installer", "driver", "runtime", "framework", "redist", "debug",
		"release", "amd64", "x86", "plugins", "extensions",
	},
}

var listFiles = map[string]string{
	"blocklist":         "blocklist.txt",
	"ignored_dirs":      "ignored_dirs.txt",
	"prog_runtimes":     "prog_runtimes.txt",
	"bad_path_keywords": "bad_path_keywords.txt",
}

func (a *App) GetSettingsBundle() (SettingsBundle, error) {
	ini, err := loadINI(configFilePath())
	if err != nil {
		return SettingsBundle{}, err
	}
	settings := mergeDefaults(ini["Settings"], defaultSettings)
	rules := mergeDefaults(ini["Rules"], defaultRules)
	lists := map[string][]string{}
	for key, file := range listFiles {
		values, err := loadListFile(filepath.Join(configDir(), file), defaultLists[key])
		if err != nil {
			return SettingsBundle{}, err
		}
		lists[key] = values
	}
	return SettingsBundle{
		Settings: settings,
		Rules:    rules,
		Lists:    lists,
		Paths: map[string]string{
			"projectRoot": projectRoot(),
			"configFile":  configFilePath(),
			"userDB":      userDatabasePath(),
			"cacheDB":     cacheDatabasePath(),
		},
	}, nil
}

func (a *App) SaveSettingsBundle(bundle SettingsBundle) error {
	if err := os.MkdirAll(configDir(), 0755); err != nil {
		return err
	}
	ini := map[string]map[string]string{
		"Settings": mergeDefaults(bundle.Settings, defaultSettings),
		"Rules":    mergeDefaults(bundle.Rules, defaultRules),
	}
	if err := saveINI(configFilePath(), ini); err != nil {
		return err
	}
	for key, file := range listFiles {
		values := bundle.Lists[key]
		if len(values) == 0 {
			values = defaultLists[key]
		}
		if err := saveListFile(filepath.Join(configDir(), file), values); err != nil {
			return err
		}
	}
	return nil
}

func loadINI(path string) (map[string]map[string]string, error) {
	result := map[string]map[string]string{}
	for section := range map[string]bool{"Settings": true, "Rules": true} {
		result[section] = map[string]string{}
	}
	file, err := os.Open(path)
	if os.IsNotExist(err) {
		return result, nil
	}
	if err != nil {
		return nil, err
	}
	defer file.Close()

	section := "Settings"
	scanner := bufio.NewScanner(file)
	for scanner.Scan() {
		line := strings.TrimSpace(scanner.Text())
		if line == "" || strings.HasPrefix(line, "#") || strings.HasPrefix(line, ";") {
			continue
		}
		if strings.HasPrefix(line, "[") && strings.HasSuffix(line, "]") {
			section = strings.TrimSpace(strings.TrimSuffix(strings.TrimPrefix(line, "["), "]"))
			if result[section] == nil {
				result[section] = map[string]string{}
			}
			continue
		}
		key, value, ok := strings.Cut(line, "=")
		if !ok {
			continue
		}
		result[section][strings.TrimSpace(key)] = strings.TrimSpace(value)
	}
	return result, scanner.Err()
}

func saveINI(path string, data map[string]map[string]string) error {
	var builder strings.Builder
	for _, section := range []string{"Settings", "Rules"} {
		builder.WriteString("[")
		builder.WriteString(section)
		builder.WriteString("]\n")
		keys := make([]string, 0, len(data[section]))
		for key := range data[section] {
			keys = append(keys, key)
		}
		sort.Strings(keys)
		for _, key := range keys {
			builder.WriteString(key)
			builder.WriteString(" = ")
			builder.WriteString(data[section][key])
			builder.WriteString("\n")
		}
		builder.WriteString("\n")
	}
	return os.WriteFile(path, []byte(builder.String()), 0644)
}

func mergeDefaults(value, defaults map[string]string) map[string]string {
	merged := map[string]string{}
	for key, def := range defaults {
		merged[key] = def
	}
	for key, val := range value {
		merged[key] = val
	}
	return merged
}

func loadListFile(path string, defaults []string) ([]string, error) {
	file, err := os.Open(path)
	if os.IsNotExist(err) {
		return sortedUnique(defaults), nil
	}
	if err != nil {
		return nil, err
	}
	defer file.Close()
	values := []string{}
	scanner := bufio.NewScanner(file)
	for scanner.Scan() {
		line := strings.TrimSpace(scanner.Text())
		if line != "" && !strings.HasPrefix(line, "#") {
			values = append(values, line)
		}
	}
	return sortedUnique(values), scanner.Err()
}

func saveListFile(path string, values []string) error {
	values = sortedUnique(values)
	return os.WriteFile(path, []byte(strings.Join(values, "\n")+"\n"), 0644)
}

func sortedUnique(values []string) []string {
	seen := map[string]bool{}
	result := []string{}
	for _, value := range values {
		clean := strings.TrimSpace(value)
		if clean == "" {
			continue
		}
		key := strings.ToLower(clean)
		if !seen[key] {
			seen[key] = true
			result = append(result, clean)
		}
	}
	// Keep configuration lists deterministic while treating casing consistently.
	// A plain sort.Strings would place upper-case entries before lower-case ones
	// (for example, "Beta" before "alpha"), which is surprising for users and
	// makes case-insensitive de-duplication non-deterministic across edits.
	sort.SliceStable(result, func(i, j int) bool {
		left, right := strings.ToLower(result[i]), strings.ToLower(result[j])
		if left == right {
			return result[i] < result[j]
		}
		return left < right
	})
	return result
}
