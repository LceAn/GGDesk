import os
import win32com.client
import re
import configparser
from collections import defaultdict

# --- 常量定义 ---
DEFAULT_OUTPUT_FOLDER_NAME = "MyTestShortcuts"
CONFIG_FILE = "config.ini"
FILENAME_BLOCKLIST = "blocklist.txt"
FILENAME_IGNORED_DIRS = "ignored_dirs.txt"

DEFAULT_BLOCKLIST = {
    'uninstall.exe', 'unins000.exe', 'unins001.exe', 'unins002.exe',
    'setup.exe', 'install.exe', 'update.exe', 'updater.exe',
    'vcredist_x64.exe', 'vcredist_x86.exe', 'vc_redist.x64.exe', 'vc_redist.x86.exe',
    'crashpad_handler.exe', 'errorreporter.exe', 'report.exe', 'config.exe'
}

DEFAULT_IGNORED_DIRS = {
    'node_modules', '.git', '.svn', '.idea', '.vscode', '__pycache__',
    'venv', 'env', 'dist', 'build', 'tmp', 'temp',
    'Windows', 'ProgramData', '$RECYCLE.BIN', 'System Volume Information'
}


# --- 快捷方式核心 ---
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


# --- 列表加载/保存通用函数 ---
def _load_set_from_file(filename, default_set):
    result_set = set(default_set)
    if os.path.exists(filename):
        try:
            with open(filename, 'r') as f:
                for line in f:
                    if line.strip(): result_set.add(line.strip())  # 注意：目录名可能区分大小写，暂时保持原样
            return result_set, f"从 {filename} 加载了 {len(result_set)} 条规则。"
        except Exception as e:
            return result_set, f"加载 {filename} 失败: {e}"
    else:
        _save_set_to_file(filename, result_set)
        return result_set, f"已创建默认规则文件: {filename}。"


def _save_set_to_file(filename, data_set):
    try:
        with open(filename, 'w') as f:
            for item in sorted(data_set): f.write(f"{item}\n")
        return True, "规则已保存。"
    except Exception as e:
        return False, f"写入失败: {e}"


# --- 公开的加载/保存接口 ---
def load_blocklist():
    # 黑名单建议转小写处理
    s, m = _load_set_from_file(FILENAME_BLOCKLIST, DEFAULT_BLOCKLIST)
    return {x.lower() for x in s}, m


def save_blocklist(s):
    return _save_set_to_file(FILENAME_BLOCKLIST, s)


def load_ignored_dirs():
    # 目录名通常保持原样比较好，或者根据系统特性
    return _load_set_from_file(FILENAME_IGNORED_DIRS, DEFAULT_IGNORED_DIRS)


def save_ignored_dirs(s):
    return _save_set_to_file(FILENAME_IGNORED_DIRS, s)


# --- 配置文件 ---
def load_config():
    config = configparser.ConfigParser()
    if os.path.exists(CONFIG_FILE):
        config.read(CONFIG_FILE, encoding='utf-8')
    if 'Settings' not in config: config['Settings'] = {}
    return config


def save_config(config):
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            config.write(f)
    except Exception as e:
        print(f"Config Error: {e}")


# --- 评分与扫描 ---
def smart_rank_executables(program_name, exe_paths, root_path):
    clean_name = re.sub(r'[_\-\s\d\.]+', '', program_name.lower())
    if not clean_name: clean_name = program_name.lower()

    scored_list = []
    for path in exe_paths:
        score = 0
        filename = os.path.basename(path).lower()
        name_no_ext = os.path.splitext(filename)[0]

        if name_no_ext == program_name.lower():
            score += 100
        elif name_no_ext == clean_name:
            score += 90
        elif clean_name in name_no_ext:
            score += 50
        elif name_no_ext in clean_name:
            score += 30

        if name_no_ext in ['launcher', 'main', 'start', 'app']: score += 20
        if '64' in name_no_ext: score += 5

        rel_path = os.path.relpath(path, root_path)
        depth = rel_path.count(os.path.sep)
        score -= (depth * 10)

        negative_keywords = ['helper', 'console', 'server', 'agent', 'service', 'tool', 'crash', 'update', 'handler']
        for kw in negative_keywords:
            if kw in name_no_ext: score -= 50

        scored_list.append((score, path))

    scored_list.sort(key=lambda x: x[0], reverse=True)
    return [x[1] for x in scored_list]


def discover_programs(scan_path, blocklist, ignored_dirs, log_callback, check_stop_callback=None):
    exe_folders = defaultdict(list)
    all_exes_data = {}

    log_callback(f"--- [Beta 4.0] 启动扫描: {scan_path} ---")

    for root, dirs, files in os.walk(scan_path, topdown=True):
        if check_stop_callback and check_stop_callback():
            log_callback("!!! 用户中止扫描 !!!")
            return []

        # 目录剪枝：使用传入的 ignored_dirs
        # 注意：Windows下路径大小写不敏感，建议统一转小写比较，或者保持原样
        # 这里做一个简单的包含检查
        dirs[:] = [d for d in dirs if d not in ignored_dirs and not d.startswith('.')]

        current_exes = []
        for file in files:
            if file.lower().endswith(".exe"):
                if file.lower() in blocklist: continue
                try:
                    full_path = os.path.join(root, file)
                    size_bytes = os.path.getsize(full_path)
                    current_exes.append(full_path)
                    all_exes_data[full_path] = (full_path, file, size_bytes, os.path.relpath(root, scan_path))
                except:
                    pass
        if current_exes:
            exe_folders[root] = current_exes

    if not exe_folders:
        log_callback("未找到有效程序。")
        return []

    sorted_folders = sorted(exe_folders.keys())
    top_level_folders = []
    if sorted_folders:
        last = sorted_folders[0]
        top_level_folders.append(last)
        for curr in sorted_folders[1:]:
            if not curr.startswith(last + os.path.sep):
                top_level_folders.append(curr)
                last = curr

    log_callback(f"定位到 {len(top_level_folders)} 个程序组，正在评分...")

    program_groups = defaultdict(list)
    program_roots = {}

    for folder in top_level_folders:
        folder_name = os.path.basename(folder)
        if folder_name.lower() == 'bin':
            root = os.path.dirname(folder)
            name = os.path.basename(root)
        else:
            root = folder
            name = folder_name

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

        prog_data = {
            'name': name,
            'root_path': root,
            'all_exes': [all_exes_data[p] for p in ranked_exes],
            'selected_exes': selected
        }
        final_programs.append(prog_data)

    log_callback(f"分析完成，生成 {len(final_programs)} 个结果。")
    return sorted(final_programs, key=lambda p: p['name'])