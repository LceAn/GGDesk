# scanner_backend/const.py

DEFAULT_OUTPUT_FOLDER_NAME = "MyTestShortcuts"
CONFIG_FILE = "config.ini"
FILENAME_BLOCKLIST = "blocklist.txt"
FILENAME_IGNORED_DIRS = "ignored_dirs.txt"

# 数据库文件
DB_FILE_USER = "user_data.db"
DB_FILE_CACHE = "cache.db"

DEFAULT_CONFIG = {
    'enable_blacklist': 'true',
    'enable_ignored_dirs': 'true',
    'enable_size_filter': 'false',
    'min_size_kb': '0',
    'max_size_mb': '500',
    'target_extensions': '.exe',
    'enable_deduplication': 'true',
    'default_check_new': 'true',
    'default_check_existing': 'false',
    'enable_smart_root': 'true',
    'is_first_run': 'true',

    # 【Beta 7.2 新增】 视觉与排序配置
    'launcher_icon_size': '72',  # 图标大小 (px)
    'launcher_show_badges': 'true',  # 是否显示来源角标 (暂未实装绘制逻辑，先留开关)
    'launcher_sort_by': 'name',  # name (名称), count (频率), added (时间)
    'sidebar_collapsed': 'false'  # 侧边栏折叠状态
}

# ... (Blocklist 和 Ignored Dirs 保持不变)
DEFAULT_BLOCKLIST = {'uninstall.exe', 'unins000.exe', 'setup.exe', 'install.exe', 'update.exe', 'updater.exe',
                     'crashpad_handler.exe', 'errorreporter.exe', 'report.exe', 'config.exe', 'splash.exe',
                     'unitycrashhandler64.exe'}
DEFAULT_IGNORED_DIRS = {'node_modules', '.git', '.svn', '.idea', '.vscode', '__pycache__', 'venv', 'env', 'dist',
                        'build', 'tmp', 'temp', 'jbr', 'jre', 'lib', 'plugins', 'Windows', 'ProgramData',
                        '$RECYCLE.BIN', 'System Volume Information'}