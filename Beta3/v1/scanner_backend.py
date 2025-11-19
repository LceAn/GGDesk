import os
import win32com.client
import re
import configparser
from collections import defaultdict

# --- 1. 配置项与常量 ---
DEFAULT_OUTPUT_FOLDER_NAME = "MyTestShortcuts"
CONFIG_FILE = "config.ini"
FILENAME_BLOCKLIST_FILE = "blocklist.txt"

DEFAULT_BLOCKLIST = {
    'uninstall.exe', 'unins000.exe', 'unins001.exe', 'unins002.exe',
    'setup.exe', 'install.exe', 'update.exe', 'updater.exe',
    'vcredist_x64.exe', 'vcredist_x86.exe', 'vc_redist.x64.exe', 'vc_redist.x86.exe',
    'crashpad_handler.exe', 'errorreporter.exe', 'report.exe', 'config.exe'
}

# 【Beta 3.2 性能优化】 扫描时强制跳过的“黑洞目录”
# 这些目录下的内容将被直接忽略，不会进入递归，极大地提升扫描速度
IGNORED_DIRS = {
    'node_modules', '.git', '.svn', '.idea', '.vscode', '__pycache__',
    'venv', 'env', 'dist', 'build', 'tmp', 'temp',
    'Windows', 'ProgramData', '$RECYCLE.BIN', 'System Volume Information'
}


# --- 2. 核心功能 ---
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


# --- 3. 黑名单逻辑 ---
def load_blocklist():
    blocklist = set(DEFAULT_BLOCKLIST)
    if os.path.exists(FILENAME_BLOCKLIST_FILE):
        try:
            with open(FILENAME_BLOCKLIST_FILE, 'r') as f:
                for line in f:
                    if line.strip(): blocklist.add(line.strip().lower())
            return blocklist, f"已加载 {len(blocklist)} 条过滤规则。"
        except Exception as e:
            return blocklist, f"[!] 读取规则失败: {e}"
    else:
        save_blocklist(blocklist)
        return blocklist, f"初始化默认规则: {FILENAME_BLOCKLIST_FILE}。"


def save_blocklist(blocklist_set):
    try:
        with open(FILENAME_BLOCKLIST_FILE, 'w') as f:
            for item in sorted(blocklist_set): f.write(f"{item}\n")
        return True, "规则已保存。"
    except Exception as e:
        return False, f"写入失败: {e}"


# --- 4. 配置文件逻辑 ---
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


# --- 5. 智能评分算法 ---
def smart_rank_executables(program_name, exe_paths, root_path):
    """
    算法：对 .exe 进行评分，分数最高的作为推荐主程序。
    """
    clean_name = re.sub(r'[_\-\s\d\.]+', '', program_name.lower())
    if not clean_name: clean_name = program_name.lower()

    scored_list = []

    for path in exe_paths:
        score = 0
        filename = os.path.basename(path).lower()
        name_no_ext = os.path.splitext(filename)[0]

        # 评分规则
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


# --- 6. 扫描逻辑 (Beta 3.2 目录剪枝优化) ---
def discover_programs(scan_path, blocklist, log_callback, check_stop_callback=None):
    exe_folders = defaultdict(list)
    all_exes_data = {}

    log_callback(f"--- [Beta 3.2] 启动极速扫描: {scan_path} ---")

    # topdown=True 是必须的，这样我们才能修改 dirs 列表以影响后续遍历
    for root, dirs, files in os.walk(scan_path, topdown=True):
        # 1. 检查停止
        if check_stop_callback and check_stop_callback():
            log_callback("!!! 用户中止扫描 !!!")
            return []

        # 2. 【Beta 3.2 核心优化】 目录剪枝 (Directory Pruning)
        # 原地修改 dirs 列表，移除黑洞目录。os.walk 下次循环将不会进入被移除的目录。
        # 我们同时过滤 IGNORED_DIRS 和以点开头(.git)的隐藏目录
        original_count = len(dirs)
        dirs[:] = [d for d in dirs if d not in IGNORED_DIRS and not d.startswith('.')]

        # (可选) 如果跳过了目录，可以在日志中体现（为了性能，这里仅在大量跳过时记录）
        # if len(dirs) < original_count:
        #    log_callback(f"跳过 {original_count - len(dirs)} 个无关目录...")

        # 3. 文件处理
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

    # 整理
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

    # 分组与评分
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