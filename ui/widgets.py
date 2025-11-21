from PySide6.QtWidgets import QPushButton, QLabel, QApplication
from PySide6.QtCore import Signal, Qt, QSize
from PySide6.QtGui import QCursor

# --- 可点击标签 ---
class ClickableLabel(QLabel):
    clicked = Signal()
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setCursor(Qt.PointingHandCursor)
    def mousePressEvent(self, event):
        self.clicked.emit()

# --- 导航按钮 ---
class NavButton(QPushButton):
    def __init__(self, text, icon_enum, parent=None):
        super().__init__(text, parent)
        self.full_text = text
        self.setObjectName("navButton")
        self.setCheckable(True)
        if icon_enum:
            self.setIcon(QApplication.style().standardIcon(icon_enum))
            self.setIconSize(QSize(20, 20))