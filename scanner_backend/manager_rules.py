import os
from .const import (
    FILENAME_BLOCKLIST, DEFAULT_BLOCKLIST,
    FILENAME_IGNORED_DIRS, DEFAULT_IGNORED_DIRS,
    DEFAULT_PROG_RUNTIMES, BAD_PATH_KEYWORDS
)

# 新增文件名常量
FILENAME_PROG_RUNTIMES = "prog_runtimes.txt"
FILENAME_BAD_PATH_KEYWORDS = "bad_path_keywords.txt"


# --- 通用 IO ---
def _load_set_from_file(filename, default_collection):
    # 将 default_collection 转为 set 以便统一处理
    default_set = set(default_collection)
    result_set = set(default_set)

    if os.path.exists(filename):
        try:
            with open(filename, 'r', encoding='utf-8') as f:
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
        with open(filename, 'w', encoding='utf-8') as f:
            for item in sorted(data_set): f.write(f"{item}\n")
        return True, "保存成功"
    except Exception as e:
        return False, f"写入失败: {e}"


# --- 具体接口 ---

# 1. 文件名黑名单
def load_blocklist():
    s, m = _load_set_from_file(FILENAME_BLOCKLIST, DEFAULT_BLOCKLIST)
    return {x.lower() for x in s}, m


def save_blocklist(s): return _save_set_to_file(FILENAME_BLOCKLIST, s)


# 2. 黑洞目录
def load_ignored_dirs():
    s, m = _load_set_from_file(FILENAME_IGNORED_DIRS, DEFAULT_IGNORED_DIRS)
    # 强制移除 bin 等关键目录 (保留之前的修复逻辑)
    BAD_IGNORES = {'bin', 'lib', 'dist', 'release'}
    s = {d for d in s if d.lower() not in BAD_IGNORES}
    return s, m


def save_ignored_dirs(s): return _save_set_to_file(FILENAME_IGNORED_DIRS, s)


# 3. 编程运行环境 (Beta 9.8 新增 IO)
def load_prog_runtimes():
    s, m = _load_set_from_file(FILENAME_PROG_RUNTIMES, DEFAULT_PROG_RUNTIMES)
    return {x.lower() for x in s}, m


def save_prog_runtimes(s): return _save_set_to_file(FILENAME_PROG_RUNTIMES, s)


# 4. 路径关键词 (Beta 9.8 新增 IO)
def load_bad_path_keywords():
    s, m = _load_set_from_file(FILENAME_BAD_PATH_KEYWORDS, BAD_PATH_KEYWORDS)
    return {x.lower() for x in s}, m


def save_bad_path_keywords(s): return _save_set_to_file(FILENAME_BAD_PATH_KEYWORDS, s)