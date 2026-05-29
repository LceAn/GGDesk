import sys
import logging
import traceback

# 配置根日志（在导入 backend 之前）
logging.basicConfig(
    level=logging.DEBUG,
    format='[%(asctime)s] %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("GGDesk")

# 全局异常钩子
def exception_hook(exc_type, exc_value, exc_tb):
    logger.critical("Unhandled exception", exc_info=(exc_type, exc_value, exc_tb))
    # 显示用户友好的错误弹窗
    try:
        from PySide6.QtWidgets import QMessageBox
        msg = f"程序发生未预期的错误:\n\n{exc_type.__name__}: {exc_value}"
        QMessageBox.critical(None, "GGDesk 错误", msg)
    except Exception:
        pass
sys.excepthook = exception_hook

import scanner_backend as backend  # 先导入 backend 以便初始化环境
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

# 必须在导入 UI 之前初始化环境，确保配置文件路径正确
backend.init_environment()

# 导入 UI (必须在环境初始化之后)
from ui.main_window import MainWindow


def main():
    # 高 DPI 支持
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName("GGDesk")
    app.setApplicationVersion("Beta 10.1")

    # 加载主题
    config = backend.load_config()
    theme = config.get('Settings', 'theme', fallback='dark')
    import scanner_styles as styles
    if theme == 'light':
        app.setStyleSheet(styles.LIGHT_QSS)
    else:
        app.setStyleSheet(styles.DARK_QSS)

    window = MainWindow()
    window.show()

    logger.info("GGDesk started successfully")
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
