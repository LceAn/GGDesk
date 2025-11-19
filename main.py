import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
# 注意：现在 MainWindow 在 ui 包里
from ui.main_window import MainWindow


def main():
    if hasattr(Qt, 'AA_EnableHighDpiScaling'): QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    app = QApplication(sys.argv)
    app.setApplicationName("ShortcutScanner")

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()