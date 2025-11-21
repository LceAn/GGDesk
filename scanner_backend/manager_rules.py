import os
from .const import FILENAME_BLOCKLIST, DEFAULT_BLOCKLIST, FILENAME_IGNORED_DIRS, DEFAULT_IGNORED_DIRS


def _load_set_from_file(filename, default_set):
    result_set = set(default_set)
    if os.path.exists(filename):
        try:
            with open(filename, 'r') as f:
                for line in f:
                    if line.strip(): result_set.add(line.strip())
            return result_set, f"加载规则完成"
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


def load_ignored_dirs():
    s, m = _load_set_from_file(FILENAME_IGNORED_DIRS, DEFAULT_IGNORED_DIRS)

    # 【Beta 9.5 强制修复】 移除可能导致扫描失效的关键目录
    # 用户如果手动加了 bin，这里会强制移除，防止误操作
    BAD_IGNORES = {'bin', 'lib', 'dist', 'release'}
    s = {d for d in s if d.lower() not in BAD_IGNORES}

    return s, m


def save_ignored_dirs(s): return _save_set_to_file(FILENAME_IGNORED_DIRS, s)