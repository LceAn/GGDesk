# scanner_backend/core_discovery.py
import os
import re
import win32com.client
from collections import defaultdict
from .manager_config import load_config


# --- 扫描源实现 ---
def scan_start_menu(blocklist):
    paths = [
        os.path.expandvars(r'%APPDATA%\Microsoft\Windows\Start Menu\Programs'),
        os.path.expandvars(r'%ProgramData%\Microsoft\Windows\Start Menu\Programs')
    ]
    results = []
    shell = win32com.client.Dispatch("WScript.Shell")
    for p in paths:
        if not os.path.exists(p): continue
        for root, _, files in os.walk(p):
            for f in files:
                if f.lower().endswith('.lnk'):
                    full_path = os.path.join(root, f)
                    try:
                        sc = shell.CreateShortCut(full_path)
                        target = sc.TargetPath
                        if target.lower().endswith('.exe'):
                            if os.path.basename(target).lower() in blocklist: continue
                            results.append(
                                {'name': os.path.splitext(f)[0], 'path': target, 'root': root, 'type': 'start_menu'})
                    except:
                        pass
    return results


def scan_uwp_apps(blocklist):
    results = []
    try:
        shell = win32com.client.Dispatch("Shell.Application")
        apps_folder = shell.NameSpace("shell:AppsFolder")
        if not apps_folder: return []
        for item in apps_folder.Items():
            name = item.Name;
            path = item.Path
            if name and path:
                results.append({'name': name, 'path': path, 'root': "Microsoft Store", 'type': 'uwp'})
    except:
        pass
    return results


# --- 智能评分 ---
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
        negative_keywords = ['helper', 'console', 'server', 'agent', 'service', 'tool', 'crash', 'update', 'handler',
                             'uninstall', 'eula']
        for kw in negative_keywords:
            if kw in name_no_ext: score -= 100
        scored_list.append((score, path))
    scored_list.sort(key=lambda x: x[0], reverse=True)
    return [x[1] for x in scored_list]


# --- 主扫描入口 ---
def discover_programs(sources, custom_path, blocklist, ignored_dirs, log_callback, check_stop_callback=None):
    conf = load_config()
    rules = conf['Rules']
    enable_dedup = rules.getboolean('enable_deduplication', True)
    enable_smart_root = rules.getboolean('enable_smart_root', True)

    seen_names = set()
    raw_results = []

    # 1. Start Menu
    if 'start_menu' in sources:
        log_callback("--- 扫描: 系统开始菜单 ---")
        items = scan_start_menu(blocklist)
        log_callback(f"  -> 发现 {len(items)} 个快捷方式")
        for item in items:
            raw_results.append(
                {'name': item['name'], 'root_path': item['root'], 'all_exes': [], 'selected_exes': (item['path'],),
                 'type': 'start_menu'})

    # 2. UWP
    if 'uwp' in sources:
        log_callback("--- 扫描: Microsoft Store ---")
        items = scan_uwp_apps(blocklist)
        log_callback(f"  -> 发现 {len(items)} 个应用")
        for item in items:
            raw_results.append(
                {'name': item['name'], 'root_path': "UWP / System", 'all_exes': [], 'selected_exes': (item['path'],),
                 'type': 'uwp'})

    # 3. Custom Path
    if 'custom' in sources and custom_path and os.path.exists(custom_path):
        log_callback(f"--- 扫描: 自定义文件夹 {custom_path} ---")
        use_size = rules.getboolean('enable_size_filter', False)
        min_kb = rules.getint('min_size_kb', 0) * 1024
        max_mb = rules.getint('max_size_mb', 500) * 1024 * 1024
        exts = [e.strip().lower() for e in rules.get('target_extensions', '.exe').split(',')]

        exe_folders = defaultdict(list);
        all_exes_data = {}
        flat_files = []

        for root, dirs, files in os.walk(custom_path, topdown=True):
            if check_stop_callback and check_stop_callback(): return []
            ignored_lower = {d.lower() for d in ignored_dirs}
            dirs[:] = [d for d in dirs if d.lower() not in ignored_lower and not d.startswith('.')]

            current_exes = []
            for file in files:
                is_target = False
                for ext in exts:
                    if file.lower().endswith(ext): is_target = True; break
                if not is_target: continue
                if file.lower() in blocklist: continue
                try:
                    full_path = os.path.join(root, file)
                    size = os.path.getsize(full_path)
                    if use_size and (size < min_kb or size > max_mb): continue

                    current_exes.append(full_path)
                    all_exes_data[full_path] = (full_path, file, size, os.path.relpath(root, custom_path))

                    if not enable_smart_root: flat_files.append(full_path)
                except:
                    pass

            if enable_smart_root and current_exes: exe_folders[root] = current_exes

        if enable_smart_root:
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

            for root, exe_paths in program_groups.items():
                name = program_roots[root]
                ranked_exes = smart_rank_executables(name, exe_paths, root)
                selected = tuple([ranked_exes[0]]) if ranked_exes else ()
                raw_results.append(
                    {'name': name, 'root_path': root, 'all_exes': [all_exes_data[p] for p in ranked_exes],
                     'selected_exes': selected, 'type': 'custom'})
        else:
            for path in flat_files:
                name = os.path.splitext(os.path.basename(path))[0]
                raw_results.append({
                    'name': name,
                    'root_path': os.path.dirname(path),
                    'all_exes': [],
                    'selected_exes': (path,),
                    'type': 'custom'
                })

    final_results = []
    if enable_dedup:
        for item in raw_results:
            name_key = item['name'].lower()
            if name_key in seen_names: continue
            seen_names.add(name_key)
            final_results.append(item)
    else:
        final_results = raw_results

    log_callback(f"扫描完成，共汇总 {len(final_results)} 个结果。")
    return sorted(final_results, key=lambda p: p['name'])