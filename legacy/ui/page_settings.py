from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QTextEdit, QFrame, QComboBox, QApplication,
    QGroupBox, QCheckBox, QPushButton, QHBoxLayout, QMessageBox
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
        layout.setContentsMargins(28, 26, 28, 26);
        layout.setSpacing(18)
        title = QLabel("⚙️ 系统设置")
        title.setObjectName("pageTitle")
        layout.addWidget(title, 0, Qt.AlignmentFlag.AlignBottom)

        # 1. 通用设置
        g_gen = QGroupBox("通用 (General)")
        l_gen = QVBoxLayout(g_gen)

        h_theme = QHBoxLayout()
        h_theme.addWidget(QLabel("界面风格:"))
        self.cb_theme = QComboBox();
        self.cb_theme.addItems(["暗黑模式", "明亮模式", "跟随系统 (Beta)"])
        self.cb_theme.currentIndexChanged.connect(self.apply_theme)
        h_theme.addWidget(self.cb_theme);
        h_theme.addStretch()
        l_gen.addLayout(h_theme)

        self.chk_auto_start = QCheckBox("开机自动启动 (Beta)")
        self.chk_hide = QCheckBox("启动程序后自动隐藏 GGDesk")
        l_gen.addWidget(self.chk_auto_start);
        l_gen.addWidget(self.chk_hide)
        layout.addWidget(g_gen)

        # 2. 数据存储
        g_data = QGroupBox("数据存储 (Data Storage)")
        l_data = QHBoxLayout(g_data)
        l_data.addWidget(QLabel(f"当前数据库: {backend.DB_FILE_USER}"))
        l_data.addStretch()
        btn_backup = QPushButton("备份数据");
        btn_backup.setObjectName("subtleButton")
        btn_backup.clicked.connect(lambda: QMessageBox.information(self, "提示", "功能开发中..."))
        btn_reset = QPushButton("重置数据库");
        btn_reset.setObjectName("warningButton")
        btn_reset.clicked.connect(self.reset_db)
        l_data.addWidget(btn_backup);
        l_data.addWidget(btn_reset)
        layout.addWidget(g_data)

        # 3. 快捷键 (UI 占位)
        g_hot = QGroupBox("快捷键 (Hotkeys)")
        l_hot = QHBoxLayout(g_hot)
        l_hot.addWidget(QLabel("呼出主窗口: Alt + Space (暂不可改)"))
        layout.addWidget(g_hot)

        # 日志
        log_title = QLabel("📜 运行日志")
        log_title.setObjectName("sectionLabel")
        layout.addWidget(log_title);
        self.log_view = QTextEdit();
        self.log_view.setReadOnly(True)
        layout.addWidget(self.log_view)

        # Load Theme
        theme = self.config.get('Settings', 'theme', fallback='dark')
        self.cb_theme.setCurrentIndex(1 if theme == 'light' else 0)

    def apply_theme(self, idx):
        self.config['Settings']['theme'] = 'light' if idx == 1 else 'dark'
        # TODO: 实现跟随系统逻辑
        QApplication.instance().setStyleSheet(styles.LIGHT_QSS if idx == 1 else styles.DARK_QSS)
        backend.save_config(self.config)

    def reset_db(self):
        if QMessageBox.question(self, "警告", "确定要清空所有已保存的快捷方式吗？",
                                QMessageBox.Yes | QMessageBox.No) == QMessageBox.Yes:
            # TODO: 调用后端 recreate_tables
            QMessageBox.information(self, "提示", "请手动删除 user_data.db 文件后重启程序。")

    def append_log(self, msg): self.log_view.append(msg)
