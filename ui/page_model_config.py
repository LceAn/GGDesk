from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PySide6.QtCore import Qt

class ModelConfigPage(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl = QLabel("🤖 模型配置 (AI Configuration)\n[Beta 6.0 预留功能]")
        lbl.setStyleSheet("font-size: 16pt; color: #999; font-weight: bold;")
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(lbl)