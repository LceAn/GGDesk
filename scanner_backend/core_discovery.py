import os
import re
import win32com.client
from collections import defaultdict
from .manager_config import load_config
from .const import BAD_PATH_KEYWORDS


def is_junk_path(path):
    path_lower = path.lower()
    folder_name = os.path.basename(path_lower)
    for kw in BAD_PATH_KEYWORDS:
        if kw in path_lower: return True
    if len(folder_name) > 20 and re.search(r'\d', folder_name) and re.search(r'[a-z]',
                                                                             folder_name) and ' ' not in folder_name:
        return True
    return False


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
               'eula']
        for kw in neg:
            if kw in name_no_ext: score -= 100
        scored_list.append((score, path))
    scored_list.sort(key=lambda x: x[0], reverse=True)
    return [x[1] for x in scored_list]


# --- 主生成器 (Beta 9.5 实时流式版) ---
def discover_programs_generator(sources, custom_path, blocklist, ignored_dirs, check_stop_callback=None):
    conf = load_config()
    rules = conf['Rules']

    # 读取配置
    enable_dedup = rules.getboolean('enable_deduplication', True)
    enable_smart_root = rules.getboolean('enable_smart_root', True)
    use_size = rules.getboolean('enable_size_filter', False)
    min_kb = rules.getint('min_size_kb', 0) * 1024
    max_mb = rules.getint('max_size_mb', 500) * 1024 * 1024
    exts = [e.strip().lower() for e in rules.get('target_extensions', '.exe').split(',')]

    # 实时去重记录 {name: priority}
    seen_names = {}
    # 源优先级：Custom(3) > UWP(2) > StartMenu(1)
    source_priority = {'custom': 3, 'uwp': 2, 'start_menu': 1}

    # --- 内部函数：处理并立即 Yield ---
    def process_and_yield(item):
        if enable_dedup:
            key = item['name'].lower()
            prio = source_priority.get(item.get('type', 'custom'), 0)

            if key in seen_names:
                # 如果已存在，且新来的优先级更低，直接忽略
                if prio <= seen_names[key]:
                    return
                # 如果新来的优先级更高（这在流式处理中比较难办，因为旧的已经yield出去了）
                # 这里的妥协方案：流式模式下，为了保证实时性，我们遵循“先到先得”或者“容忍重复”
                # 但为了效果，我们可以在 UI 层做二次去重，或者在这里记录。
                # 简单起见：这里只做拦截。
                pass

            seen_names[key] = prio

        # 立即输出！
        yield item

    # 1. Start Menu
    if 'start_menu' in sources:
        for item in scan_start_menu(blocklist):
            if check_stop_callback and check_stop_callback(): return
            # 构造数据并立即处理
            res = {'name': item['name'], 'root_path': item['root'], 'all_exes': [], 'selected_exes': (item['path'],),
                   'type': 'start_menu'}
            yield from process_and_yield(res)

    # 2. UWP
    if 'uwp' in sources:
        for item in scan_uwp_apps(blocklist):
            if check_stop_callback and check_stop_callback(): return
            res = {'name': item['name'], 'root_path': "UWP / System", 'all_exes': [], 'selected_exes': (item['path'],),
                   'type': 'uwp'}
            yield from process_and_yield(res)

    # 3. Custom Path
    if 'custom' in sources and custom_path and os.path.exists(custom_path):
        ignored_lower = {d.lower() for d in ignored_dirs}

        for root, dirs, files in os.walk(custom_path, topdown=True):
            if check_stop_callback and check_stop_callback(): return

            # 剪枝：跳过垃圾目录
            if is_junk_path(root):
                dirs[:] = []
                continue

            # 剪枝：跳过用户忽略目录
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
                    if use_size and (sz < min_kb or size > max_mb): continue

                    # 模式 A: 平铺 (关闭智能识别) -> 立即 Yield
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
                        # 模式 B: 智能识别 -> 收集当前文件夹
                        current_exes.append((full, file, sz))
                except:
                    pass

            # 智能模式：单文件夹处理完，立即分析并 Yield
            # 这实现了“文件夹级”的实时流，而不是全盘扫描后的延迟显示
            if enable_smart_root and current_exes:
                folder_name = os.path.basename(root)
                # 处理 bin 目录反查上一级
                if folder_name.lower() == 'bin':
                    program_name = os.path.basename(os.path.dirname(root))
                else:
                    program_name = folder_name

                # 评分
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