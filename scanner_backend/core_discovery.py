import os
import re
import win32com.client
from collections import defaultdict
from .manager_config import load_config
# 【Beta 9.8】 不再直接导入常量，改为导入 IO 函数
from .manager_rules import load_bad_path_keywords, load_prog_runtimes
from .core_dedup import deduplicate_programs


# --- 辅助：判断是否为垃圾路径 ---
def is_junk_path(path, bad_keywords):
    """
    智能判断当前路径是否为组件/缓存/运行时目录
    bad_keywords: 从文件加载的动态集合
    """
    path_lower = path.lower()
    folder_name = os.path.basename(path_lower)

    # 1. 关键词匹配 (动态)
    for kw in bad_keywords:
        if kw in path_lower:
            return True

    # 2. 哈希/乱码文件夹检测 (静态逻辑)
    if len(folder_name) > 20 and re.search(r'\d', folder_name) and re.search(r'[a-z]',
                                                                             folder_name) and ' ' not in folder_name:
        return True
    return False


# ... (scan_start_menu, scan_uwp_apps, smart_rank_executables 保持不变，省略以节省篇幅) ...
# 请保留原有的 scan_start_menu, scan_uwp_apps, smart_rank_executables 函数代码不变
def scan_start_menu(blocklist):
    paths = [os.path.expandvars(r'%APPDATA%\Microsoft\Windows\Start Menu\Programs'),
             os.path.expandvars(r'%ProgramData%\Microsoft\Windows\Start Menu\Programs')]
    shell = win32com.client.Dispatch("WScript.Shell")
    for p in paths:
        if not os.path.exists(p): continue
        for root, _, files in os.walk(p):
            for f in files:
                if f.lower().endswith('.lnk'):
                    try:
                        target = shell.CreateShortCut(os.path.join(root, f)).TargetPath
                        if target.lower().endswith('.exe'):
                            if os.path.basename(target).lower() not in blocklist:
                                yield {'name': os.path.splitext(f)[0], 'path': target, 'root': root,
                                       'type': 'start_menu'}
                    except:
                        pass


def scan_uwp_apps(blocklist):
    try:
        shell = win32com.client.Dispatch("Shell.Application")
        apps = shell.NameSpace("shell:AppsFolder")
        if apps:
            for item in apps.Items():
                if item.Name and item.Path:
                    if item.Name.lower() + ".exe" not in blocklist:
                        yield {'name': item.Name, 'path': item.Path, 'root': "Microsoft Store", 'type': 'uwp'}
    except:
        pass


def smart_rank_executables(program_name, exe_paths, root_path):
    tokens = [t.lower() for t in re.split(r'[_\-\s\.]+', program_name) if len(t) > 1 and not t.isdigit()]
    clean_name = re.sub(r'[_\-\s\d\.]+', '', program_name.lower())
    scored_list = []
    for path in exe_paths:
        score = 0
        filename = os.path.basename(path).lower()
        name_no_ext = os.path.splitext(filename)[0]
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
        if filename.endswith('.exe'): score += 5
        rel_path = os.path.relpath(path, root_path)
        score -= (rel_path.count(os.path.sep) * 15)
        neg = ['helper', 'console', 'server', 'agent', 'service', 'tool', 'crash', 'update', 'handler', 'uninstall',
               'eula', 'reporter']
        for kw in neg:
            if kw in name_no_ext: score -= 100
        scored_list.append((score, path))
    scored_list.sort(key=lambda x: x[0], reverse=True)
    return [x[1] for x in scored_list]


# --- 主生成器 (Beta 9.8) ---
def discover_programs_generator(sources, custom_path, blocklist, ignored_dirs, check_stop_callback=None):
    conf = load_config()
    rules = conf['Rules']

    enable_dedup = rules.getboolean('enable_deduplication', True)
    enable_smart_root = rules.getboolean('enable_smart_root', True)
    use_size = rules.getboolean('enable_size_filter', False)
    min_kb = rules.getint('min_size_kb', 0) * 1024
    max_mb = rules.getint('max_size_mb', 500) * 1024 * 1024

    exts = [e.strip().lower() for e in rules.get('target_extensions', '.exe').split(',')]

    # 【Beta 9.8】 动态加载规则
    filter_prog = rules.getboolean('enable_prog_filter', True)
    prog_runtimes, _ = load_prog_runtimes()

    filter_bad_path = rules.getboolean('enable_bad_path', True)  # 新增配置项
    bad_path_kws, _ = load_bad_path_keywords()

    seen_names = {}
    source_priority = {'custom': 3, 'uwp': 2, 'start_menu': 1}

    def process_and_yield(item):
        if enable_dedup:
            key = item['name'].lower()
            prio = source_priority.get(item.get('type', 'custom'), 0)
            if key in seen_names and prio <= seen_names[key]: return
            seen_names[key] = prio
        yield item

    if 'start_menu' in sources:
        for item in scan_start_menu(blocklist):
            if check_stop_callback and check_stop_callback(): return
            res = {'name': item['name'], 'root_path': item['root'], 'all_exes': [], 'selected_exes': (item['path'],),
                   'type': 'start_menu'}
            yield from process_and_yield(res)

    if 'uwp' in sources:
        for item in scan_uwp_apps(blocklist):
            if check_stop_callback and check_stop_callback(): return
            res = {'name': item['name'], 'root_path': "UWP / System", 'all_exes': [], 'selected_exes': (item['path'],),
                   'type': 'uwp'}
            yield from process_and_yield(res)

    if 'custom' in sources and custom_path and os.path.exists(custom_path):
        ignored_lower = {d.lower() for d in ignored_dirs}

        for root, dirs, files in os.walk(custom_path, topdown=True):
            if check_stop_callback and check_stop_callback(): return

            # 【Beta 9.8】 动态判断垃圾目录
            if filter_bad_path and is_junk_path(root, bad_path_kws):
                dirs[:] = []
                continue

            dirs[:] = [d for d in dirs if d.lower() not in ignored_lower and not d.startswith('.')]

            current_exes = []
            for file in files:
                is_target = False
                for ext in exts:
                    if file.lower().endswith(ext): is_target = True; break
                if not is_target: continue
                if file.lower() in blocklist: continue

                # 【Beta 9.8】 动态判断编程环境
                if filter_prog and file.lower() in prog_runtimes: continue

                try:
                    full = os.path.join(root, file)
                    sz = os.path.getsize(full)
                    if use_size and (sz < min_kb or size > max_mb): continue

                    if not enable_smart_root:
                        res = {
                            'name': os.path.splitext(file)[0],
                            'root_path': root,
                            'all_exes': [],
                            'selected_exes': (full,),
                            'type': 'custom'
                        }
                        yield from process_and_yield(res)
                    else:
                        current_exes.append((full, file, sz))
                except:
                    pass

            if enable_smart_root and current_exes:
                folder_name = os.path.basename(root)
                if folder_name.lower() == 'bin':
                    program_name = os.path.basename(os.path.dirname(root))
                else:
                    program_name = folder_name

                exe_paths = [x[0] for x in current_exes]
                ranked = smart_rank_executables(program_name, exe_paths, root)
                details = []
                for p in ranked:
                    s = 0
                    for x in current_exes:
                        if x[0] == p: s = x[2]; break
                    details.append((p, os.path.basename(p), s, os.path.relpath(p, custom_path)))

                res = {
                    'name': program_name,
                    'root_path': root,
                    'all_exes': details,
                    'selected_exes': tuple([ranked[0]]) if ranked else (),
                    'type': 'custom'
                }
                yield from process_and_yield(res)