from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QTextEdit, QFrame, QComboBox, QApplication
)
from PySide6.QtCore import Qt
import scanner_backend as backend
import scanner_styles as styles


class SettingsPage(QWidget):
    def __init__(self):
        super().__init__()
        self.config = backend.load_config()
        self.build_ui()

    def build_ui(self):
        layout = QVBoxLayout(self);
        layout.setContentsMargins(30, 30, 30, 30);
        layout.setSpacing(20)

        g1 = QFrame();
        l1 = QVBoxLayout(g1);
        l1.addWidget(QLabel("🎨 界面风格"))
        self.theme_combo = QComboBox();
        self.theme_combo.addItems(["暗黑模式 (Dark)", "明亮模式 (Light)"])
        self.theme_combo.currentIndexChanged.connect(self.apply_theme);
        l1.addWidget(self.theme_combo);
        layout.addWidget(g1)

        layout.addWidget(QLabel("📜 运行日志"));
        self.log_view = QTextEdit();
        self.log_view.setReadOnly(True);
        self.log_view.setObjectName("logArea")
        layout.addWidget(self.log_view)

        # Load Theme
        theme = self.config.get('Settings', 'theme', fallback='dark')
        self.theme_combo.setCurrentIndex(1 if theme == 'light' else 0)
        self.apply_theme(self.theme_combo.currentIndex())

    def apply_theme(self, idx):
        self.config['Settings']['theme'] = 'light' if idx == 1 else 'dark'
        QApplication.instance().setStyleSheet(styles.LIGHT_QSS if idx == 1 else styles.DARK_QSS)
        backend.save_config(self.config)

    def append_log(self, msg):
        self.log_view.append(msg)