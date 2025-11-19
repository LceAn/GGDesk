import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from ui.main_window import MainWindow


def main():
    # PySide6 6.0+ 自动处理 HighDPI，无需手动设置属性
    # 直接初始化应用
    app = QApplication(sys.argv)
    app.setApplicationName("GGDesk")

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()