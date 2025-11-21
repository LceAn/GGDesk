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

    # 视觉配置
    'launcher_icon_size': '72',
    'launcher_show_badges': 'true',
    'launcher_sort_by': 'name',
    'sidebar_collapsed': 'false'
}

# 文件名黑名单
DEFAULT_BLOCKLIST = {
    'uninstall.exe', 'unins000.exe', 'unins001.exe', 'setup.exe', 'install.exe',
    'update.exe', 'updater.exe', 'config.exe', 'splash.exe',
    'crashpad_handler.exe', 'errorreporter.exe', 'report.exe',
    'unitycrashhandler64.exe', 'nwjc.exe', 'chromedriver.exe',
    'netcorecheck.exe', 'vcredist_x64.exe', 'vcredist_x86.exe',
    'elevate.exe', 'runner.exe', 'notification_helper.exe'
}

# 【Beta 8.1.1 修复】 移除 'bin', 'lib', 'dist' 等可能包含主程序的目录
DEFAULT_IGNORED_DIRS = {
    'node_modules', '.git', '.svn', '.idea', '.vscode', '__pycache__',
    'venv', 'env', 'tmp', 'temp', 'cache', 'logs',
    'jbr', 'jre', 'obj', 'properties', 'runtimes', 'packages',
    'Windows', 'ProgramData', '$RECYCLE.BIN', 'System Volume Information',
    'Microsoft Visual Studio', 'Common7', 'MSBuild'
}

# 路径关键词过滤 (包含即跳过)
BAD_PATH_KEYWORDS = [
    'runtime', 'framework', 'redist', 'prerequisites', 'installer',
    'debug', 'release', 'amd64', 'x86', 'plugins', 'extensions',
    'sha256', 'checksum', 'hash'
]