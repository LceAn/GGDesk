from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QPushButton
)
from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices, QCursor


class AboutDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("关于 GGDesk")
        self.setFixedSize(400, 250)
        # 显式设置标志，确保关闭按钮可用
        self.setWindowFlags(Qt.Dialog | Qt.WindowCloseButtonHint)

        self.build_ui()

    def build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(30, 30, 30, 30)

        # 标题
        lbl_title = QLabel("GGDesk Shortcut Scanner")
        lbl_title.setStyleSheet("font-size: 16pt; font-weight: bold; color: #0078D7;")
        lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(lbl_title)

        # 版本号
        lbl_ver = QLabel("Version: Beta 9.2 (Refactored)")
        lbl_ver.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(lbl_ver)

        # GitHub 按钮
        btn_gh = QPushButton("🔗 GitHub 仓库")
        btn_gh.setCursor(Qt.PointingHandCursor)
        btn_gh.clicked.connect(lambda: QDesktopServices.openUrl(QUrl("https://github.com/LceAn/GGDesk")))

        # 作者按钮
        btn_auth = QPushButton("👤 开发者主页 (LceAn)")
        btn_auth.setCursor(Qt.PointingHandCursor)
        btn_auth.clicked.connect(lambda: QDesktopServices.openUrl(QUrl("https://github.com/LceAn")))

        layout.addWidget(btn_gh)
        layout.addWidget(btn_auth)
        layout.addStretch()