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
	IncludeUWP       bool   `json:"includeUWP"`
	Limit            int    `json:"limit"`
}

type ScanResult struct {
	Name         string       `json:"name"`
	ExePath      string       `json:"exePath"`
	LnkPath      string       `json:"lnkPath"`
	Args         string       `json:"args"`
	SelectedExes []string     `json:"selectedExes"`
	AllExes      []ScanExeInfo `json:"allExes"`
	SourceType   string       `json:"sourceType"`
	RootPath     string       `json:"rootPath"`
	Category     string       `json:"category"`
	Status       string       `json:"status"`
	Selected     bool         `json:"selected"`
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

// LogFrontend 供前端把日志/错误传到后端 stderr（无 devtools 时的调试通道）。
func (a *App) LogFrontend(message string) {
	fmt.Println("[FRONTEND]", message)
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

	// SQLite 单写特性：强制串行连接，避免连接池多连接互相争锁导致 SQLITE_BUSY。
	// 通过 _pragma 设置：busy_timeout（遇锁等待5秒）、WAL 模式、NORMAL 同步。
	// modernc.org/sqlite 会优先处理 busy_timeout pragma（见其 driver.go 注释）。
	dsn := dbPath + "?_pragma=busy_timeout(5000)&_pragma=journal_mode(WAL)&_pragma=synchronous(NORMAL)"
	db, err := sql.Open("sqlite", dsn)
	if err != nil {
		return err
	}
	db.SetMaxOpenConns(1)
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

	// 加载配置驱动扫描：[Rules] 开关 + 四个列表文件。
	rules, lists, err := a.loadScanRules()
	if err != nil {
		// 配置缺失不致命，降级到默认规则。
		rules = defaultScanRules()
		lists = defaultScanLists()
	}

	// 预处理列表为 map/set，便于快速查找。
	blocklist := toLowerSet(lists["blocklist"])
	ignoredDirs := toLowerSet(lists["ignored_dirs"])
	progRuntimes := toLowerSet(lists["prog_runtimes"])
	badPathKws := lists["bad_path_keywords"]

	results := []ScanResult{}
	// 扫描期去重：同名项按源优先级保留高优先级（custom>uwp>start_menu）。
	seen := map[string]int{}

	add := func(result ScanResult) bool {
		if len(results) >= limit {
			return false
		}
		key := strings.ToLower(result.Name)
		if prio, found := seen[key]; found {
			if sourcePriority(result.SourceType) <= prio {
				return true // 优先级不高于已存在项，丢弃。
			}
			// 优先级更高，移除旧的同类项。
			for i, r := range results {
				if strings.ToLower(r.Name) == key {
					results = append(results[:i], results[i+1:]...)
					break
				}
			}
		}
		seen[key] = sourcePriority(result.SourceType)

		// 计算状态：是否已入库。
		exeKey := normalizeTarget(result.ExePath)
		lnkKey := normalizeTarget(result.LnkPath)
		if (exeKey != "" && existing[exeKey]) || (lnkKey != "" && existing[lnkKey]) {
			result.Status = "已存在"
			result.Selected = stringsEqualFold(rules["default_check_existing"], "true")
		} else {
			result.Status = "新增"
			result.Selected = stringsEqualFold(rules["default_check_new"], "true")
		}
		result.Category = SuggestCategory(result.Name, result.ExePath, result.SourceType)
		// UWP 的 args 由 AppID 推导。
		result.Args = uwpArgs(result)
		results = append(results, result)
		return true
	}

	// --- 开始菜单源：解析 .lnk 真实目标 ---
	if options.IncludeStartMenu {
		if stopped := a.scanStartMenu(blocklist, rules, add); stopped {
			sortAndFinalize(results)
			return results, nil
		}
	}

	// --- UWP 源：枚举 shell:AppsFolder ---
	if options.IncludeUWP {
		if stopped := a.scanUWP(blocklist, add); stopped {
			sortAndFinalize(results)
			return results, nil
		}
	}

	// --- 自定义目录源：smart_root 评分 / 平铺 ---
	custom := strings.TrimSpace(options.CustomPath)
	if custom != "" {
		a.scanCustom(custom, blocklist, ignoredDirs, progRuntimes, badPathKws, rules, add)
	}

	sortAndFinalize(results)
	return results, nil
}

func sortAndFinalize(results []ScanResult) {
	sort.SliceStable(results, func(i, j int) bool {
		if results[i].Status != results[j].Status {
			return results[i].Status == "新增"
		}
		return strings.ToLower(results[i].Name) < strings.ToLower(results[j].Name)
	})
}

// scanStartMenu 枚举开始菜单的 .lnk 并解析真实目标。
// 返回 true 表示因达到 limit 提前终止。
func (a *App) scanStartMenu(blocklist map[string]bool, rules map[string]string, add func(ScanResult) bool) bool {
	var lnkFiles []string
	for _, root := range expandStartMenuRoots() {
		_ = filepath.WalkDir(root, func(path string, d os.DirEntry, err error) error {
			if err != nil {
				return nil
			}
			if d.IsDir() {
				return nil
			}
			if strings.EqualFold(filepath.Ext(path), ".lnk") {
				lnkFiles = append(lnkFiles, path)
			}
			return nil
		})
	}
	// 批量解析提升性能（单次 COM 初始化）。
	targets := resolveShortcutsBatch(lnkFiles)
	for i, lnk := range lnkFiles {
		target := targets[i]
		if target == "" || !strings.EqualFold(filepath.Ext(target), ".exe") {
			continue
		}
		base := strings.ToLower(filepath.Base(target))
		if blocklist[base] {
			continue
		}
		name := strings.TrimSuffix(filepath.Base(lnk), filepath.Ext(lnk))
		if !add(ScanResult{
			Name:       name,
			ExePath:    target,
			LnkPath:    lnk,
			SourceType: "start_menu",
			RootPath:   filepath.Dir(lnk),
		}) {
			return true
		}
	}
	return false
}

// scanUWP 枚举 Microsoft Store 应用。
func (a *App) scanUWP(blocklist map[string]bool, add func(ScanResult) bool) bool {
	apps, err := enumerateUWPApps()
	if err != nil {
		return false
	}
	for _, app := range apps {
		// UWP 的 "exe 名" 约定为 AppID+".exe" 以复用黑名单逻辑。
		if blocklist[strings.ToLower(app.AppID)+".exe"] {
			continue
		}
		if !add(ScanResult{
			Name:       app.Name,
			ExePath:    app.AppID,
			SourceType: "uwp",
			RootPath:   "Microsoft Store",
		}) {
			return true
		}
	}
	return false
}

// scanCustom 扫描自定义目录。smart_root 开启时每目录评分选最优 exe。
func (a *App) scanCustom(customPath string, blocklist, ignoredDirs, progRuntimes map[string]bool, badPathKws []string, rules map[string]string, add func(ScanResult) bool) {
	exts := parseTargetExtensions(rules["target_extensions"])
	if len(exts) == 0 {
		exts = []string{".exe"}
	}
	smartRoot := stringsEqualFold(rules["enable_smart_root"], "true")
	useSize := stringsEqualFold(rules["enable_size_filter"], "true")
	minBytes := atoiSafe(rules["min_kb"]) * 1024
	maxBytes := atoiSafe(rules["max_mb"]) * 1024 * 1024
	filterProg := stringsEqualFold(rules["enable_prog_filter"], "true")
	filterBadPath := stringsEqualFold(rules["enable_bad_path"], "true")

	// smart_root 模式按目录聚合候选；否则平铺逐个输出。两者共用一次遍历。
	byDir := map[string][]ScanExeInfo{}
	dirOrder := []string{}

	_ = filepath.WalkDir(customPath, func(path string, d os.DirEntry, err error) error {
		if err != nil {
			return nil
		}
		name := d.Name()
		nameLower := strings.ToLower(name)

		if d.IsDir() {
			if path == customPath {
				return nil
			}
			// 黑洞目录精确匹配 + 隐藏目录 + 动态垃圾路径。
			if ignoredDirs[nameLower] || strings.HasPrefix(name, ".") {
				return filepath.SkipDir
			}
			if filterBadPath && isJunkPath(path, badPathKws) {
				return filepath.SkipDir
			}
			return nil
		}

		// 扩展名 / 黑名单精确文件名 / 编程运行时过滤。
		ext := strings.ToLower(filepath.Ext(name))
		if !containsFold(exts, ext) {
			return nil
		}
		if blocklist[nameLower] {
			return nil
		}
		if filterProg && progRuntimes[nameLower] {
			return nil
		}
		info, serr := d.Info()
		if serr != nil {
			return nil
		}
		size := info.Size()
		if useSize && (size < int64(minBytes) || size > int64(maxBytes)) {
			return nil
		}

		full := path
		if !smartRoot {
			// 平铺模式：直接列出每个 exe。
			add(ScanResult{
				Name:         strings.TrimSuffix(name, filepath.Ext(name)),
				ExePath:      full,
				SourceType:   "custom",
				RootPath:     filepath.Dir(full),
				AllExes:      []ScanExeInfo{{Path: full, Name: name, Size: size, RelPath: relPath(full, customPath)}},
				SelectedExes: []string{full},
			})
			return nil
		}

		// smart_root 模式：按目录收集候选。
		dir := filepath.Dir(path)
		if _, ok := byDir[dir]; !ok {
			dirOrder = append(dirOrder, dir)
		}
		byDir[dir] = append(byDir[dir], ScanExeInfo{
			Path:    full,
			Name:    name,
			Size:    size,
			RelPath: relPath(full, customPath),
		})
		return nil
	})

	// smart_root 后处理：每目录评分选最优。
	for _, dir := range dirOrder {
		candidates := byDir[dir]
		if len(candidates) == 0 {
			continue
		}
		folderName := filepath.Base(dir)
		programName := folderName
		if strings.ToLower(folderName) == "bin" {
			programName = filepath.Base(filepath.Dir(dir))
		}
		ranked := smartRankExecutables(programName, candidates, dir)
		selected := ""
		if len(ranked) > 0 {
			selected = ranked[0].Path
		}
		selectedList := []string{}
		if selected != "" {
			selectedList = append(selectedList, selected)
		}
		add(ScanResult{
			Name:         programName,
			ExePath:      selected,
			SourceType:   "custom",
			RootPath:     dir,
			AllExes:      ranked,
			SelectedExes: selectedList,
		})
	}
}

func (a *App) loadScanRules() (map[string]string, map[string][]string, error) {
	bundle, err := a.GetSettingsBundle()
	if err != nil {
		return nil, nil, err
	}
	return bundle.Rules, bundle.Lists, nil
}

func defaultScanRules() map[string]string {
	return mergeDefaults(map[string]string{}, defaultRules)
}

func defaultScanLists() map[string][]string {
	out := map[string][]string{}
	for k, v := range defaultLists {
		out[k] = v
	}
	return out
}

func sourcePriority(t string) int {
	switch t {
	case "custom":
		return 3
	case "uwp":
		return 2
	case "start_menu":
		return 1
	}
	return 0
}

func parseTargetExtensions(value string) []string {
	parts := strings.Split(value, ",")
	exts := []string{}
	for _, p := range parts {
		e := strings.TrimSpace(strings.ToLower(p))
		if e != "" {
			exts = append(exts, e)
		}
	}
	return exts
}

func containsFold(list []string, target string) bool {
	for _, v := range list {
		if strings.EqualFold(v, target) {
			return true
		}
	}
	return false
}

func toLowerSet(items []string) map[string]bool {
	set := map[string]bool{}
	for _, item := range items {
		key := strings.TrimSpace(strings.ToLower(item))
		if key != "" {
			set[key] = true
		}
	}
	return set
}

func stringsEqualFold(a, b string) bool {
	return strings.EqualFold(strings.TrimSpace(a), strings.TrimSpace(b))
}

func atoiSafe(s string) int {
	s = strings.TrimSpace(s)
	n := 0
	for _, r := range s {
		if r < '0' || r > '9' {
			break
		}
		n = n*10 + int(r-'0')
	}
	return n
}

func relPath(full, base string) string {
	rel, err := filepath.Rel(base, full)
	if err != nil {
		return full
	}
	return rel
}

// uwpArgs 为 UWP 类型的结果生成 shell:AppsFolder 启动参数。
func uwpArgs(r ScanResult) string {
	if r.SourceType == "uwp" && r.ExePath != "" && !looksLikeFilesystemPath(r.ExePath) {
		return "shell:AppsFolder\\" + r.ExePath
	}
	return ""
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
				VALUES (?, ?, ?, ?, ?, ?, ?)`, name, r.ExePath, r.LnkPath, r.SourceType, r.Args, category, time.Now().Format(time.RFC3339))
		} else if err == nil {
			_, err = tx.Exec(`UPDATE shortcuts SET name = ?, lnk_path = ?, source_type = ?, args = ?, category = ? WHERE id = ?`,
				name, r.LnkPath, r.SourceType, r.Args, category, id)
		}
		if err != nil {
			return count, err
		}
		count++
	}
	return count, tx.Commit()
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
