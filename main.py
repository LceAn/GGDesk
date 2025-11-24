import sys
import scanner_backend as backend  # 先导入 backend 以便初始化环境
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

# 必须在导入 UI 之前初始化环境，确保配置文件路径正确
backend.init_environment()

# 导入 UI (必须在环境初始化之后)
from ui.main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("GGDesk")

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()