# main.py
import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
import scanner_styles as styles
from scanner_ui import MainWindow


def main():
    # 启用高分屏支持
    if hasattr(Qt, 'AA_EnableHighDpiScaling'):
        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    if hasattr(Qt, 'AA_UseHighDpiPixmaps'):
        QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)
    app.setApplicationName("ShortcutScanner")

    # 启动主窗口
    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()