from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QTextEdit, QFrame, QComboBox, QApplication,
    QGroupBox, QCheckBox, QPushButton, QHBoxLayout, QMessageBox, QFileDialog,
    QProgressBar
)
from PySide6.QtCore import Qt, QTimer
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

        # === 1. 外观 ===
        g_gen = QGroupBox("🎨 外观 (Appearance)")
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

        # === 2. 数据概览 ===
        g_stats = QGroupBox("📊 数据概览 (Statistics)")
        l_stats = QVBoxLayout(g_stats)

        # 统计标签
        stats_grid = QHBoxLayout()
        self.lbl_total = QLabel("--")
        self.lbl_total.setStyleSheet("font-size: 18pt; font-weight: bold; color: #0078D7;")
        self.lbl_runs = QLabel("--")
        self.lbl_runs.setStyleSheet("font-size: 18pt; font-weight: bold; color: #2E8B57;")
        self.lbl_db_size = QLabel("--")
        self.lbl_db_size.setStyleSheet("font-size: 14pt; color: #888;")

        col1 = QVBoxLayout()
        col1.addWidget(QLabel("已收录应用"))
        col1.addWidget(self.lbl_total)

        col2 = QVBoxLayout()
        col2.addWidget(QLabel("累计启动次数"))
        col2.addWidget(self.lbl_runs)

        col3 = QVBoxLayout()
        col3.addWidget(QLabel("数据库大小"))
        col3.addWidget(self.lbl_db_size)

        stats_grid.addLayout(col1)
        stats_grid.addLayout(col2)
        stats_grid.addStretch()
        stats_grid.addLayout(col3)
        l_stats.addLayout(stats_grid)

        layout.addWidget(g_stats)

        # === 3. 数据维护 ===
        g_data = QGroupBox("🛠️ 数据维护 (Data Maintenance)")
        l_data = QVBoxLayout(g_data)

        info_row = QHBoxLayout()
        info_row.addWidget(QLabel(f"数据库: {backend.DB_FILE_USER}"))
        l_data.addLayout(info_row)

        btn_row1 = QHBoxLayout()
        btn_backup = QPushButton("📦 备份数据库")
        btn_backup.clicked.connect(self.backup_database)
        btn_restore = QPushButton("📂 恢复备份")
        btn_restore.clicked.connect(self.restore_database)
        btn_row1.addWidget(btn_backup)
        btn_row1.addWidget(btn_restore)
        l_data.addLayout(btn_row1)

        btn_row2 = QHBoxLayout()
        btn_clear_cache = QPushButton("🧹 清理图标缓存")
        btn_clear_cache.clicked.connect(self.clear_icon_cache)
        btn_vacuum = QPushButton("🔧 压缩数据库")
        btn_vacuum.clicked.connect(self.vacuum_database)
        l_data.addLayout(btn_row2)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setFrameShadow(QFrame.Shadow.Sunken)
        l_data.addWidget(sep)

        btn_row3 = QHBoxLayout()
        btn_row3.addStretch()
        btn_reset = QPushButton("⚠️ 重置所有数据")
        btn_reset.setStyleSheet("color: red; border: 1px solid red;")
        btn_reset.clicked.connect(self.reset_db)
        btn_row3.addWidget(btn_reset)
        l_data.addLayout(btn_row3)

        layout.addWidget(g_data)

        # === 4. 快捷键 ===
        g_hot = QGroupBox("⌨️ 快捷键 (Hotkeys)")
        l_hot = QHBoxLayout(g_hot)
        l_hot.addWidget(QLabel("呼出主窗口:"))
        lbl_key = QLabel("Alt + Space")
        lbl_key.setStyleSheet("font-weight: bold; color: #0078D7; padding: 2px 8px; "
                               "background: rgba(0,120,215,0.1); border-radius: 4px;")
        lbl_key2 = QLabel("(暂不可改)")
        lbl_key2.setStyleSheet("color: #888;")
        l_hot.addWidget(lbl_key)
        l_hot.addWidget(lbl_key2)
        l_hot.addStretch()
        layout.addWidget(g_hot)

        # === 5. 日志 ===
        layout.addWidget(QLabel("📜 运行日志"))
        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setMaximumHeight(200)
        layout.addWidget(self.log_view)

        # 加载
        theme = self.config.get('Settings', 'theme', fallback='dark')
        self.cb_theme.setCurrentIndex(1 if theme == 'light' else 0)
        QTimer.singleShot(100, self.refresh_stats)

    def refresh_stats(self):
        """刷新数据统计"""
        try:
            stats = backend.get_shortcut_stats()
            self.lbl_total.setText(str(stats['total']))
            self.lbl_runs.setText(str(stats['total_runs']))
            size = backend.get_db_size()
            if size < 1024:
                self.lbl_db_size.setText(f"{size} B")
            elif size < 1024 * 1024:
                self.lbl_db_size.setText(f"{size / 1024:.1f} KB")
            else:
                self.lbl_db_size.setText(f"{size / 1024 / 1024:.2f} MB")
        except Exception:
            pass

    def apply_theme(self, idx):
        self.config['Settings']['theme'] = 'light' if idx == 1 else 'dark'
        QApplication.instance().setStyleSheet(styles.LIGHT_QSS if idx == 1 else styles.DARK_QSS)
        backend.save_config(self.config)

    def backup_database(self):
        if not os.path.exists(backend.DB_FILE_USER):
            QMessageBox.information(self, "提示", "数据库文件不存在，无需备份。")
            return
        default_name = f"ggdesk_backup_{os.path.basename(backend.DB_FILE_USER)}"
        path, _ = QFileDialog.getSaveFileName(self, "选择备份位置", default_name,
                                              "SQLite 数据库 (*.db);;所有文件 (*)")
        if path:
            try:
                shutil.copy2(backend.DB_FILE_USER, path)
                for ext in ['-wal', '-shm']:
                    f = backend.DB_FILE_USER + ext
                    if os.path.exists(f):
                        shutil.copy2(f, path + ext)
                QMessageBox.information(self, "备份成功", f"已备份到:\n{path}")
                self.append_log(f"[Settings] 数据库备份成功 → {path}")
            except Exception as e:
                QMessageBox.warning(self, "备份失败", str(e))

    def restore_database(self):
        path, _ = QFileDialog.getOpenFileName(self, "选择备份文件", "",
                                              "SQLite 数据库 (*.db);;所有文件 (*)")
        if not path:
            return
        if QMessageBox.question(self, "确认恢复",
                                "恢复将覆盖当前所有数据，是否继续？",
                                QMessageBox.Yes | QMessageBox.No) == QMessageBox.No:
            return
        try:
            shutil.copy2(path, backend.DB_FILE_USER)
            backend.init_databases()
            QMessageBox.information(self, "恢复成功", "已恢复，请重启程序生效。")
            self.refresh_stats()
        except Exception as e:
            QMessageBox.warning(self, "恢复失败", str(e))

    def clear_icon_cache(self):
        if QMessageBox.question(self, "清理图标缓存",
                                "将清空图标缓存数据，程序会在下次启动时重新生成。\n是否继续？",
                                QMessageBox.Yes | QMessageBox.No) == QMessageBox.Yes:
            if backend.clear_cache_db():
                QMessageBox.information(self, "完成", "图标缓存已清理。")
                self.refresh_stats()
                self.append_log("[Settings] 图标缓存已清理")
            else:
                QMessageBox.warning(self, "失败", "清理失败，缓存数据库可能不存在。")

    def vacuum_database(self):
        if QMessageBox.question(self, "压缩数据库",
                                "将回收数据库碎片空间，操作期间可能短暂卡顿。\n是否继续？",
                                QMessageBox.Yes | QMessageBox.No) == QMessageBox.Yes:
            if backend.vacuum_databases():
                QMessageBox.information(self, "完成", "数据库压缩完成。")
                self.refresh_stats()
                self.append_log("[Settings] 数据库已压缩")
            else:
                QMessageBox.warning(self, "失败", "压缩失败。")

    def reset_db(self):
        if QMessageBox.question(self, "⚠️ 危险操作",
                                "确定要清空所有已保存的快捷方式和分类数据吗？\n\n此操作不可撤销！",
                                QMessageBox.Yes | QMessageBox.No) == QMessageBox.Yes:
            try:
                os.remove(backend.DB_FILE_USER)
                for ext in ['-wal', '-shm']:
                    f = backend.DB_FILE_USER + ext
                    if os.path.exists(f):
                        os.remove(f)
                backend.init_databases()
                self.append_log("[Settings] 数据库已重置")
                self.refresh_stats()
                QMessageBox.information(self, "完成", "数据库已重置。")
            except Exception as e:
                QMessageBox.warning(self, "重置失败", str(e))

    def append_log(self, msg):
        self.log_view.append(msg)
