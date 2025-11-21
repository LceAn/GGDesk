import os
import re
import win32com.client
from collections import defaultdict
from .manager_config import load_config
from .const import BAD_PATH_KEYWORDS
from .core_dedup import deduplicate_programs  # 导入去重模块


# --- 辅助判断 ---
def is_junk_path(path):
    path_lower = path.lower()
    folder_name = os.path.basename(path_lower)
    for kw in BAD_PATH_KEYWORDS:
        if kw in path_lower: return True
    if len(folder_name) > 20 and re.search(r'\d', folder_name) and re.search(r'[a-z]',
                                                                             folder_name) and ' ' not in folder_name:
        return True
    return False


# --- 扫描源实现 ---
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


# --- 智能评分 (Beta 7.4 Logic) ---
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
               'eula']
        for kw in neg:
            if kw in name_no_ext: score -= 100
        scored_list.append((score, path))
    scored_list.sort(key=lambda x: x[0], reverse=True)
    return [x[1] for x in scored_list]


# --- 主生成器 (修复版) ---
def discover_programs_generator(sources, custom_path, blocklist, ignored_dirs, check_stop_callback=None):
    conf = load_config()
    rules = conf['Rules']
    enable_smart_root = rules.getboolean('enable_smart_root', True)
    enable_dedup = rules.getboolean('enable_deduplication', True)
    use_size = rules.getboolean('enable_size_filter', False)
    min_kb = rules.getint('min_size_kb', 0) * 1024
    max_mb = rules.getint('max_size_mb', 500) * 1024 * 1024
    exts = [e.strip().lower() for e in rules.get('target_extensions', '.exe').split(',')]

    # 临时存储列表，用于去重
    all_found_items = []

    # 1. Start Menu
    if 'start_menu' in sources:
        for item in scan_start_menu(blocklist):
            if check_stop_callback and check_stop_callback(): return
            res = {'name': item['name'], 'root_path': item['root'], 'all_exes': [], 'selected_exes': (item['path'],),
                   'type': 'start_menu'}
            all_found_items.append(res)
            if not enable_dedup: yield res  # 如果不去重，直接抛出

    # 2. UWP
    if 'uwp' in sources:
        for item in scan_uwp_apps(blocklist):
            if check_stop_callback and check_stop_callback(): return
            res = {'name': item['name'], 'root_path': "UWP / System", 'all_exes': [], 'selected_exes': (item['path'],),
                   'type': 'uwp'}
            all_found_items.append(res)
            if not enable_dedup: yield res

    # 3. Custom Path (回归 Beta 7.4 的逻辑，修复自定义扫描失效问题)
    if 'custom' in sources and custom_path and os.path.exists(custom_path):
        ignored_lower = {d.lower() for d in ignored_dirs}
        exe_folders = defaultdict(list)
        all_exes_data = {}
        flat_files = []

        # 遍历
        for root, dirs, files in os.walk(custom_path, topdown=True):
            if check_stop_callback and check_stop_callback(): return

            if is_junk_path(root):
                dirs[:] = []
                continue
            dirs[:] = [d for d in dirs if d.lower() not in ignored_lower and not d.startswith('.')]

            current_exes = []
            for file in files:
                is_target = False
                for ext in exts:
                    if file.lower().endswith(ext): is_target = True; break
                if not is_target or file.lower() in blocklist: continue

                try:
                    full = os.path.join(root, file)
                    sz = os.path.getsize(full)
                    if use_size and (sz < min_kb or sz > max_mb): continue

                    current_exes.append(full)
                    all_exes_data[full] = (full, file, sz, os.path.relpath(root, custom_path))
                    if not enable_smart_root: flat_files.append(full)
                except:
                    pass

            if enable_smart_root and current_exes: exe_folders[root] = current_exes

        # 处理逻辑：智能分组 vs 平铺
        custom_results = []
        if enable_smart_root:
            # 排序并找到顶层目录 (Key Logic restored from Beta 7.4)
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
                # 处理 bin 目录回溯
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

            for root, exe_paths in program_groups.items():
                name = program_roots[root]
                ranked = smart_rank_executables(name, exe_paths, root)
                sel = tuple([ranked[0]]) if ranked else ()
                # 构造详细数据
                details = [all_exes_data[p] for p in ranked]
                custom_results.append(
                    {'name': name, 'root_path': root, 'all_exes': details, 'selected_exes': sel, 'type': 'custom'})
        else:
            # 平铺模式
            for path in flat_files:
                custom_results.append({
                    'name': os.path.splitext(os.path.basename(path))[0],
                    'root_path': os.path.dirname(path),
                    'all_exes': [],
                    'selected_exes': (path,),
                    'type': 'custom'
                })

        all_found_items.extend(custom_results)
        if not enable_dedup:
            for res in custom_results: yield res

    # 4. 执行去重并 Yield (如果开启了去重)
    if enable_dedup:
        deduplicated = deduplicate_programs(all_found_items)
        for item in deduplicated:
            yield item