import os
import win32com.client
import re
import configparser
from collections import defaultdict

# --- 1. 配置项与常量 ---
OUTPUT_FOLDER_NAME = "MyTestShortcuts"
CONFIG_FILE = "config.ini"
FILENAME_BLOCKLIST_FILE = "blocklist.txt"
DEFAULT_BLOCKLIST = {
    'uninstall.exe', 'unins000.exe', 'unins001.exe', 'unins002.exe',
    'setup.exe', 'install.exe', 'update.exe', 'updater.exe',
    'vcredist_x64.exe', 'vcredist_x86.exe', 'vc_redist.x64.exe', 'vc_redist.x86.exe',
    'crashpad_handler.exe', 'errorreporter.exe', 'report.exe',
}

# --- 2. 核心功能 ---
def create_shortcut(target_path, shortcut_path):
    """
    使用 win32com 创建一个 .lnk 快捷方式
    返回 (bool: success, str: message)
    """
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

# --- 3. 黑名单逻辑 (纯IO) ---
def load_blocklist():
    """
    从 blocklist.txt 加载黑名单
    返回 (set: blocklist, str: status_message)
    """
    blocklist = set(DEFAULT_BLOCKLIST)
    if os.path.exists(FILENAME_BLOCKLIST_FILE):
        try:
            with open(FILENAME_BLOCKLIST_FILE, 'r') as f:
                for line in f:
                    if line.strip():
                        blocklist.add(line.strip().lower())
            return blocklist, f"已从 {FILENAME_BLOCKLIST_FILE} 加载 {len(blocklist)} 条规则。"
        except Exception as e:
            return blocklist, f"[!] 加载 {FILENAME_BLOCKLIST_FILE} 失败: {e}"
    else:
        # 如果文件不存在，创建一个默认的
        status = save_blocklist(blocklist)
        return blocklist, f"未找到黑名单，已创建默认: {FILENAME_BLOCKLIST_FILE}。{status[1]}"

def save_blocklist(blocklist_set):
    """
    将黑名单集合保存到文件
    返回 (bool: success, str: message)
    """
    try:
        with open(FILENAME_BLOCKLIST_FILE, 'w') as f:
            for item in sorted(blocklist_set):
                f.write(f"{item}\n")
        return True, "黑名单已保存。"
    except Exception as e:
        return False, f"无法写入 {FILENAME_BLOCKLIST_FILE}:\n{e}"

# --- 4. 【新】v8.1 配置文件逻辑 ---
def load_config():
    """加载 config.ini"""
    config = configparser.ConfigParser()
    if os.path.exists(CONFIG_FILE):
        config.read(CONFIG_FILE)
    
    # 确保 'Settings' 节存在
    if 'Settings' not in config:
        config['Settings'] = {}
        
    return config

def save_config(config):
    """保存 config.ini"""
    try:
        with open(CONFIG_FILE, 'w') as configfile:
            config.write(configfile)
    except Exception as e:
        print(f"警告：无法保存配置 {CONFIG_FILE}: {e}") # 后端日志

# --- 5. 核心 v7 扫描逻辑 (已解耦) ---

def run_v6_heuristic(program_name, exe_paths):
    """v6 启发式：基于文件夹名的匹配"""
    keywords = set(re.split(r'[_\-\s\d.]+', program_name.lower()))
    keywords.discard('')
    
    if not keywords:
        return []
        
    suggestions = []
    for path in exe_paths:
        exe_name = os.path.basename(path).lower()
        for key in keywords:
            if key in exe_name:
                suggestions.append(path)
                break 
    
    suggestions.sort(key=len)
    return suggestions[:1] # 只建议最好的 1 个

def discover_programs(scan_path, blocklist, log_callback):
    """
    v7 核心算法：程序发现
    log_callback 是一个函数，如 print 或 UI的log方法，用于接收日志
    """
    # 1. 递归扫描，收集所有 .exe 及其文件夹
    exe_folders = defaultdict(list)
    all_exes_data = {} 
    
    log_callback(f"--- 开始程序发现: {scan_path} ---")
    for root, dirs, files in os.walk(scan_path, topdown=True):
        current_exes = []
        for file in files:
            if file.lower().endswith(".exe"):
                if file.lower() in blocklist:
                    log_callback(f"[过滤] {os.path.join(root, file)}")
                    continue
                
                try:
                    full_path = os.path.join(root, file)
                    size_bytes = os.path.getsize(full_path)
                    current_exes.append(full_path)
                    all_exes_data[full_path] = (full_path, file, size_bytes, os.path.relpath(root, scan_path))
                except (IOError, OSError) as e:
                    log_callback(f"[!] 无法访问: {file} | {e}")
                        
        if current_exes:
            exe_folders[root] = current_exes

    if not exe_folders:
        log_callback("未找到任何 (未被过滤的) .exe 文件。")
        return []

    # 2. 找到“顶层”的 .exe 文件夹 (过滤掉子文件夹)
    sorted_folders = sorted(exe_folders.keys())
    top_level_folders = []
    if sorted_folders:
        last_folder = sorted_folders[0]
        top_level_folders.append(last_folder)
        for current_folder in sorted_folders[1:]:
            if not current_folder.startswith(last_folder + os.path.sep):
                top_level_folders.append(current_folder)
                last_folder = current_folder
    
    log_callback(f"发现 {len(top_level_folders)} 个顶层 .exe 目录...")

    # 3. 确定“程序根目录” (bin 逻辑)
    program_groups = defaultdict(list)
    program_roots = {} 
    
    for folder in top_level_folders:
        folder_name = os.path.basename(folder)
        if folder_name.lower() == 'bin':
            program_root = os.path.dirname(folder)
            program_name = os.path.basename(program_root)
        else:
            program_root = folder
            program_name = folder_name
        
        is_subpath = False
        for existing_root in list(program_roots.keys()):
            if program_root.startswith(existing_root + os.path.sep):
                is_subpath = True
                break 
            if existing_root.startswith(program_root + os.path.sep):
                del program_roots[existing_root]
        
        if not is_subpath:
            program_roots[program_root] = program_name

    # 4. 将所有 .exe 分配到它们所属的“程序根目录”
    for full_path in all_exes_data.keys():
        matching_root = None
        for root in program_roots.keys():
            if full_path.startswith(root + os.path.sep):
                if matching_root is None or len(root) > len(matching_root):
                    matching_root = root
        if matching_root:
            program_groups[matching_root].append(full_path)

    # 5. 格式化最终数据，并运行 v6 启发式
    final_programs = []
    for root, exe_paths in program_groups.items():
        name = program_roots[root]
        suggested_exes = run_v6_heuristic(name, exe_paths)
        
        program_data = {
            'name': name,
            'root_path': root,
            'all_exes': [all_exes_data[path] for path in exe_paths], 
            'selected_exes': tuple(suggested_exes) 
        }
        final_programs.append(program_data)
    
    log_callback(f"--- 发现完成 ---")
    log_callback(f"总共发现 {len(final_programs)} 个潜在程序组。")
    return sorted(final_programs, key=lambda p: p['name'])