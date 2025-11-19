import os
import win32com.client
import re
import configparser
from collections import defaultdict

# --- 1. 配置项与常量 ---
DEFAULT_OUTPUT_FOLDER_NAME = "MyTestShortcuts"
CONFIG_FILE = "config.ini"
FILENAME_BLOCKLIST = "blocklist.txt"
FILENAME_IGNORED_DIRS = "ignored_dirs.txt"

# 默认配置值
DEFAULT_CONFIG = {
    'enable_blacklist': 'true',
    'enable_ignored_dirs': 'true',
    'enable_size_filter': 'false',
    'min_size_kb': '0',
    'max_size_mb': '500',
    'target_extensions': '.exe',  # 逗号分隔，如 .exe,.bat
    'scan_mode': 'custom'  # custom, start_menu, uwp
}

DEFAULT_BLOCKLIST = {
    'uninstall.exe', 'unins000.exe', 'unins001.exe', 'unins002.exe',
    'setup.exe', 'install.exe', 'update.exe', 'updater.exe',
    'vcredist_x64.exe', 'vcredist_x86.exe', 'vc_redist.x64.exe', 'vc_redist.x86.exe',
    'crashpad_handler.exe', 'errorreporter.exe', 'report.exe', 'config.exe',
    'splash.exe', 'unitycrashhandler64.exe'
}

DEFAULT_IGNORED_DIRS = {
    'node_modules', '.git', '.svn', '.idea', '.vscode', '__pycache__',
    'venv', 'env', 'dist', 'build', 'tmp', 'temp', 'jbr', 'jre', 'lib', 'plugins',
    'Windows', 'ProgramData', '$RECYCLE.BIN', 'System Volume Information'
}


# --- 2. 核心功能 (快捷方式/打开) ---
def create_shortcut(target_path, shortcut_path):
    try:
        shell = win32com.client.Dispatch("WScript.Shell")
        shortcut = shell.CreateShortCut(shortcut_path)
        shortcut.TargetPath = target_path
        shortcut.WorkingDirectory = os.path.dirname(target_path)
        shortcut.IconLocation = target_path
        shortcut.Save()
        return True, f"成功: {os.path.basename(shortcut_path)}"
    except Exception as e:
        return False, f"失败: {os.path.basename(target_path)} | {e}"


def open_file_explorer(path):
    if not os.path.exists(path): return
    try:
        os.startfile(path)
    except Exception as e:
        print(f"无法打开文件夹: {e}")


def scan_existing_shortcuts(folder_path):
    results = []
    if not os.path.exists(folder_path): return results
    try:
        shell = win32com.client.Dispatch("WScript.Shell")
        for file in os.listdir(folder_path):
            if file.lower().endswith(".lnk"):
                full_path = os.path.join(folder_path, file)
                try:
                    shortcut = shell.CreateShortCut(full_path)
                    results.append((file, shortcut.TargetPath))
                except:
                    results.append((file, "无法读取目标"))
    except:
        pass
    return results


def normalize_path(path):
    if not path: return ""
    return os.path.normpath(os.path.abspath(path)).lower()


# --- 3. IO 逻辑 ---
def _load_set_from_file(filename, default_set):
    result_set = set(default_set)
    if os.path.exists(filename):
        try:
            with open(filename, 'r') as f:
                for line in f:
                    if line.strip(): result_set.add(line.strip())
            return result_set, f"加载 {len(result_set)} 条规则"
        except:
            return result_set, "加载失败"
    else:
        _save_set_to_file(filename, result_set)
        return result_set, "创建默认规则"


def _save_set_to_file(filename, data_set):
    try:
        with open(filename, 'w') as f:
            for item in sorted(data_set): f.write(f"{item}\n")
        return True, "保存成功"
    except Exception as e:
        return False, f"写入失败: {e}"


def load_blocklist():
    s, m = _load_set_from_file(FILENAME_BLOCKLIST, DEFAULT_BLOCKLIST)
    return {x.lower() for x in s}, m


def save_blocklist(s): return _save_set_to_file(FILENAME_BLOCKLIST, s)


def load_ignored_dirs(): return _load_set_from_file(FILENAME_IGNORED_DIRS, DEFAULT_IGNORED_DIRS)


def save_ignored_dirs(s): return _save_set_to_file(FILENAME_IGNORED_DIRS, s)


# --- 4. 配置文件 (Beta 5.0 增强) ---
def load_config():
    config = configparser.ConfigParser()
    if os.path.exists(CONFIG_FILE): config.read(CONFIG_FILE, encoding='utf-8')
    if 'Settings' not in config: config['Settings'] = {}
    if 'Rules' not in config: config['Rules'] = {}  # 新增 Rules 节点

    # 填充默认值
    for k, v in DEFAULT_CONFIG.items():
        if k not in config['Rules']: config['Rules'][k] = v

    return config


def save_config(config):
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            config.write(f)
    except Exception as e:
        print(f"Config Error: {e}")


# --- 5. 智能评分 ---
def smart_rank_executables(program_name, exe_paths, root_path):
    tokens = [t.lower() for t in re.split(r'[_\-\s\.]+', program_name) if len(t) > 1 and not t.isdigit()]
    clean_name = re.sub(r'[_\-\s\d\.]+', '', program_name.lower())
    scored_list = []

    for path in exe_paths:
        score = 0
        filename = os.path.basename(path).lower()
        name_no_ext = os.path.splitext(filename)[0]

        # 基础分
        for token in tokens:
            if token == name_no_ext:
                score += 150
            elif token in name_no_ext:
                score += 80
        if name_no_ext == clean_name:
            score += 100
        elif clean_name in name_no_ext:
            score += 50
        if name_no_ext in ['launcher', 'main', 'start', 'app', 'run']: score += 20
        if '64' in name_no_ext: score += 10

        # 深度惩罚
        rel = os.path.relpath(path, root_path)
        score -= (rel.count(os.path.sep) * 15)

        # 负面词
        neg = ['helper', 'console', 'server', 'agent', 'service', 'tool', 'crash', 'update', 'handler', 'uninstall',
               'eula']
        for kw in neg:
            if kw in name_no_ext: score -= 100

        scored_list.append((score, path))

    scored_list.sort(key=lambda x: x[0], reverse=True)
    return [x[1] for x in scored_list]


# --- 6. 扫描逻辑 (Beta 5.0: 规则过滤) ---
def discover_programs(scan_path, blocklist, ignored_dirs, log_callback, check_stop_callback=None):
    # 加载规则配置
    conf = load_config()
    rules = conf['Rules']

    use_blacklist = rules.getboolean('enable_blacklist', True)
    use_ignore_dir = rules.getboolean('enable_ignored_dirs', True)

    use_size_filter = rules.getboolean('enable_size_filter', False)
    min_kb = rules.getint('min_size_kb', 0) * 1024
    max_mb = rules.getint('max_size_mb', 500) * 1024 * 1024

    exts = [e.strip().lower() for e in rules.get('target_extensions', '.exe').split(',')]

    exe_folders = defaultdict(list)
    all_exes_data = {}

    log_callback(f"--- [Beta 5.0] 启动扫描: {scan_path} ---")
    log_callback(f"规则: 黑名单={use_blacklist}, 大小过滤={use_size_filter}, 类型={exts}")

    for root, dirs, files in os.walk(scan_path, topdown=True):
        if check_stop_callback and check_stop_callback(): return []

        # 1. 目录过滤 (如果开启)
        if use_ignore_dir:
            ignored_lower = {d.lower() for d in ignored_dirs}
            dirs[:] = [d for d in dirs if d.lower() not in ignored_lower and not d.startswith('.')]

        current_exes = []
        for file in files:
            # 2. 扩展名过滤
            is_target = False
            for ext in exts:
                if file.lower().endswith(ext):
                    is_target = True
                    break
            if not is_target: continue

            # 3. 黑名单过滤 (如果开启)
            if use_blacklist and file.lower() in blocklist: continue

            try:
                full_path = os.path.join(root, file)
                size_bytes = os.path.getsize(full_path)

                # 4. 大小过滤 (如果开启)
                if use_size_filter:
                    if size_bytes < min_kb or size_bytes > max_mb:
                        continue

                current_exes.append(full_path)
                all_exes_data[full_path] = (full_path, file, size_bytes, os.path.relpath(root, scan_path))
            except:
                pass

        if current_exes: exe_folders[root] = current_exes

    if not exe_folders:
        log_callback("未找到符合条件的程序。")
        return []

    # ... (后续分组逻辑保持不变，为节省篇幅省略，逻辑与 Beta 4.3 一致) ...
    # 如果需要完整代码，我可以把分组部分也贴上，但这部分没有变动。

    # --- 分组逻辑开始 ---
    sorted_folders = sorted(exe_folders.keys())
    top_level_folders = []
    if sorted_folders:
        last = sorted_folders[0];
        top_level_folders.append(last)
        for curr in sorted_folders[1:]:
            if not curr.startswith(last + os.path.sep): top_level_folders.append(curr); last = curr

    program_groups = defaultdict(list);
    program_roots = {}
    for folder in top_level_folders:
        name = os.path.basename(os.path.dirname(folder)) if os.path.basename(
            folder).lower() == 'bin' else os.path.basename(folder)
        root = os.path.dirname(folder) if os.path.basename(folder).lower() == 'bin' else folder
        is_sub = False
        for ex_root in list(program_roots.keys()):
            if root.startswith(ex_root + os.path.sep): is_sub = True; break
            if ex_root.startswith(root + os.path.sep): del program_roots[ex_root]
        if not is_sub: program_roots[root] = name

    for full_path in all_exes_data.keys():
        match_root = None
        for root in program_roots.keys():
            if full_path.startswith(root + os.path.sep):
                if match_root is None or len(root) > len(match_root): match_root = root
        if match_root: program_groups[match_root].append(full_path)

    final_programs = []
    for root, exe_paths in program_groups.items():
        name = program_roots[root]
        ranked_exes = smart_rank_executables(name, exe_paths, root)
        selected = tuple([ranked_exes[0]]) if ranked_exes else ()
        prog_data = {'name': name, 'root_path': root, 'all_exes': [all_exes_data[p] for p in ranked_exes],
                     'selected_exes': selected}
        final_programs.append(prog_data)

    log_callback(f"完成，生成 {len(final_programs)} 个结果。")
    return sorted(final_programs, key=lambda p: p['name'])