import os
import shutil

# 导入常量
from .const import (
    DEFAULT_OUTPUT_FOLDER_NAME, DB_FILE_USER, DB_FILE_CACHE,
    DIR_CONFIG, DIR_DATA,
    CONFIG_FILE, FILENAME_BLOCKLIST, FILENAME_IGNORED_DIRS,
    FILENAME_PROG_RUNTIMES, FILENAME_BAD_PATH_KEYWORDS
)

from .utils_system import create_shortcut, open_file_explorer, scan_existing_shortcuts, normalize_path
from .manager_config import load_config, save_config
from .manager_rules import load_blocklist, save_blocklist, load_ignored_dirs, save_ignored_dirs

from .core_discovery import discover_programs_generator
from .core_dedup import deduplicate_programs

from .manager_db import (
    init_databases,
    add_shortcut_to_db,
    get_all_shortcuts,
    delete_shortcut,
    increment_run_count
)


# 【Beta 10.0】 环境初始化与文件迁移
def init_environment():
    """
    1. 创建 config/ 和 data/ 目录
    2. 将根目录下的旧配置文件/数据库迁移到新目录
    """
    # 1. 创建目录
    if not os.path.exists(DIR_CONFIG):
        os.makedirs(DIR_CONFIG)
        print(f"Created directory: {DIR_CONFIG}")

    if not os.path.exists(DIR_DATA):
        os.makedirs(DIR_DATA)
        print(f"Created directory: {DIR_DATA}")

    # 2. 定义迁移映射 (旧文件名 -> 新完整路径)
    migration_map = {
        "config.ini": CONFIG_FILE,
        "blocklist.txt": FILENAME_BLOCKLIST,
        "ignored_dirs.txt": FILENAME_IGNORED_DIRS,
        "prog_runtimes.txt": FILENAME_PROG_RUNTIMES,
        "bad_path_keywords.txt": FILENAME_BAD_PATH_KEYWORDS,
        "user_data.db": DB_FILE_USER,
        "cache.db": DB_FILE_CACHE
    }

    # 3. 执行迁移
    for old_name, new_path in migration_map.items():
        # 如果根目录有旧文件，且新目录没有同名文件 (防止覆盖新生成的)
        if os.path.exists(old_name) and os.path.isfile(old_name):
            if not os.path.exists(new_path):
                try:
                    shutil.move(old_name, new_path)
                    print(f"[Migration] Moved {old_name} -> {new_path}")
                except Exception as e:
                    print(f"[Migration Error] Could not move {old_name}: {e}")
            else:
                # 如果新旧都存在，为了整洁，甚至可以考虑把旧的重命名备份，这里暂且保留不动
                pass