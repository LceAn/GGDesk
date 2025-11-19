# scanner_backend/__init__.py

from .const import DEFAULT_OUTPUT_FOLDER_NAME
from .utils_system import create_shortcut, open_file_explorer, scan_existing_shortcuts, normalize_path
from .manager_config import load_config, save_config
from .manager_rules import load_blocklist, save_blocklist, load_ignored_dirs, save_ignored_dirs
from .core_discovery import discover_programs

# 【Beta 7.0 修复】 暴露所有数据库操作函数
from .manager_db import (
    init_databases,
    add_shortcut_to_db,
    get_all_shortcuts,
    delete_shortcut,
    increment_run_count
)