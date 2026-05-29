from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QTextEdit, QFrame, QComboBox, QApplication,
    QGroupBox, QCheckBox, QPushButton, QHBoxLayout, QMessageBox, QFileDialog
)
from PySide6.QtCore import Qt
import os
import shutil
import scanner_backend as backend
import scanner_styles as styles


class SettingsPage(QWidget):
    def __init__(self):
        super().__init__()
        self.config = backend.load_config()
        self.build_ui()

    def build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)
        layout.addWidget(QLabel("⚙️ 系统设置"), 0, Qt.AlignmentFlag.AlignBottom)

        # 1. 通用设置
        g_gen = QGroupBox("通用 (General)")
        l_gen = QVBoxLayout(g_gen)

        h_theme = QHBoxLayout()
        h_theme.addWidget(QLabel("界面风格:"))
        self.cb_theme = QComboBox()
        self.cb_theme.addItems(["暗黑模式", "明亮模式", "跟随系统 (Beta)"])
        self.cb_theme.currentIndexChanged.connect(self.apply_theme)
        h_theme.addWidget(self.cb_theme)
        h_theme.addStretch()
        l_gen.addLayout(h_theme)

        self.chk_auto_start = QCheckBox("开机自动启动 (Beta)")
        self.chk_hide = QCheckBox("启动程序后自动隐藏 GGDesk")
        l_gen.addWidget(self.chk_auto_start)
        l_gen.addWidget(self.chk_hide)
        layout.addWidget(g_gen)

        # 2. 数据存储
        g_data = QGroupBox("数据存储 (Data Storage)")
        l_data = QVBoxLayout(g_data)

        info_row = QHBoxLayout()
        info_row.addWidget(QLabel(f"数据库路径: {backend.DB_FILE_USER}"))
        l_data.addLayout(info_row)

        btn_row = QHBoxLayout()
        btn_backup = QPushButton("📦 备份数据")
        btn_backup.clicked.connect(self.backup_database)
        btn_restore = QPushButton("📂 恢复备份")
        btn_restore.clicked.connect(self.restore_database)
        btn_reset = QPushButton("🗑️ 重置数据库")
        btn_reset.setStyleSheet("color: red;")
        btn_reset.clicked.connect(self.reset_db)
        btn_row.addStretch()
        btn_row.addWidget(btn_backup)
        btn_row.addWidget(btn_restore)
        btn_row.addWidget(btn_reset)
        l_data.addLayout(btn_row)

        layout.addWidget(g_data)

        # 3. 快捷键 (UI 占位)
        g_hot = QGroupBox("快捷键 (Hotkeys)")
        l_hot = QHBoxLayout(g_hot)
        l_hot.addWidget(QLabel("呼出主窗口: Alt + Space (暂不可改)"))
        layout.addWidget(g_hot)

        # 日志
        layout.addWidget(QLabel("📜 运行日志"))
        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        layout.addWidget(self.log_view)

        # Load Theme
        theme = self.config.get('Settings', 'theme', fallback='dark')
        self.cb_theme.setCurrentIndex(1 if theme == 'light' else 0)

    def apply_theme(self, idx):
        self.config['Settings']['theme'] = 'light' if idx == 1 else 'dark'
        QApplication.instance().setStyleSheet(styles.LIGHT_QSS if idx == 1 else styles.DARK_QSS)
        backend.save_config(self.config)

    def backup_database(self):
        """备份数据库到用户指定位置"""
        default_name = f"ggdesk_backup_{os.path.basename(backend.DB_FILE_USER)}"
        if not os.path.exists(backend.DB_FILE_USER):
            QMessageBox.information(self, "提示", "数据库文件不存在，无需备份。")
            return

        path, _ = QFileDialog.getSaveFileName(
            self, "选择备份位置", default_name,
            "SQLite 数据库 (*.db);;所有文件 (*)"
        )
        if path:
            try:
                # 同时备份 WAL 和 SHM 文件（如果存在）
                shutil.copy2(backend.DB_FILE_USER, path)
                wal = backend.DB_FILE_USER + "-wal"
                shm = backend.DB_FILE_USER + "-shm"
                for extra in [wal, shm]:
                    if os.path.exists(extra):
                        shutil.copy2(extra, path + extra[extra.rfind('-'):])
                QMessageBox.information(self, "备份成功", f"数据库已备份到:\n{path}")
            except Exception as e:
                QMessageBox.warning(self, "备份失败", str(e))

    def restore_database(self):
        """从备份恢复数据库"""
        path, _ = QFileDialog.getOpenFileName(
            self, "选择备份文件", "",
            "SQLite 数据库 (*.db);;所有文件 (*)"
        )
        if not path:
            return

        if QMessageBox.question(
            self, "确认恢复",
            "恢复数据库将覆盖当前所有数据。\n是否继续？",
            QMessageBox.Yes | QMessageBox.No
        ) == QMessageBox.No:
            return

        try:
            shutil.copy2(path, backend.DB_FILE_USER)
            backend.init_databases()  # 确保表结构完整
            QMessageBox.information(self, "恢复成功", "数据库已恢复，请重启程序以生效。")
        except Exception as e:
            QMessageBox.warning(self, "恢复失败", str(e))

    def reset_db(self):
        """重置数据库 — 清空所有用户数据"""
        if QMessageBox.question(
            self, "⚠️ 危险操作",
            "确定要清空所有已保存的快捷方式和分类数据吗？\n\n此操作不可撤销！",
            QMessageBox.Yes | QMessageBox.No
        ) == QMessageBox.Yes:
            try:
                os.remove(backend.DB_FILE_USER)
                # 同时清理 WAL 和 SHM
                for ext in ['-wal', '-shm']:
                    f = backend.DB_FILE_USER + ext
                    if os.path.exists(f):
                        os.remove(f)
                backend.init_databases()
                self.append_log("[Settings] 数据库已重置")
                QMessageBox.information(self, "完成", "数据库已重置。")
            except Exception as e:
                QMessageBox.warning(self, "重置失败", str(e))

    def append_log(self, msg):
        self.log_view.append(msg)
