# scanner_backend/__init__.py

# 从各个子模块导入所有内容，暴露给外部
from .const import DEFAULT_OUTPUT_FOLDER_NAME
from .utils_system import create_shortcut, open_file_explorer, scan_existing_shortcuts, normalize_path
from .manager_config import load_config, save_config
from .manager_rules import load_blocklist, save_blocklist, load_ignored_dirs, save_ignored_dirs
from .core_discovery import discover_programs

# 这样 UI 调用 backend.load_config() 时，实际上调用的是 manager_config.load_config()