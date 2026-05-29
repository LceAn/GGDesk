import os
import re
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QStatusBar, QProgressBar,
    QStackedWidget, QApplication, QSize
)
from PySide6.QtCore import Qt, Slot
import scanner_backend as backend
import scanner_styles as styles

# 导入各个页面
from .page_scan import ScanPage
from .page_output import OutputPage
from .page_settings import SettingsPage
from .page_quick_launch import QuickLaunchPage
from .page_launch_manage import LaunchManagePage
from .page_model_config import ModelConfigPage
from .page_dedup import DedupPage
from .sidebar import Sidebar
from .dialog_welcome import WelcomeDialog
from .dialog_about import AboutDialog


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("GGDesk Beta 10.1")
        self.config = backend.load_config()
        backend.init_databases()

        self.build_ui()
        self.setup_statusbar()
        self.restore_geometry()

        if hasattr(self, 'page_output'):
            self.on_output_path_changed(self.page_output.out_edit.text())
        self.check_first_run()

    def setup_statusbar(self):
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.setStyleSheet("""
            QStatusBar { background-color: #FFFFFF; border-top: 1px solid #E5E5E5; min-height: 28px; color: #666666; }
            QStatusBar::item { border: none; }
        """)
        self.status_label = QLabel(" 就绪")
        self.status_label.setStyleSheet("padding-left: 5px;")
        self.status_bar.addWidget(self.status_label, 1)
        self.progress = QProgressBar()
        self.progress.setFixedWidth(150)
        self.progress.setFixedHeight(4)
        self.progress.setTextVisible(False)
        self.progress.setStyleSheet("""
            QProgressBar { background-color: #F0F0F0; border: none; border-radius: 2px; }
            QProgressBar::chunk { background-color: #0078D7; border-radius: 2px; }
        """)
        self.progress.setVisible(False)
        self.progress.setRange(0, 0)
        self.status_bar.addPermanentWidget(self.progress)

    def build_ui(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        root_layout = QHBoxLayout(main_widget)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # 使用复用的 Sidebar 组件
        self.sidebar = Sidebar()
        self.sidebar.page_changed.connect(self.on_nav_clicked)
        self.sidebar.about_requested.connect(self.show_about)
        root_layout.addWidget(self.sidebar)

        # Pages
        self.stack = QStackedWidget()
        self.stack.setObjectName("mainArea")

        # 页面索引必须与 Sidebar 的 add_nav_btn idx 对应
        self.page_quick = QuickLaunchPage()      # 0
        self.page_manage = LaunchManagePage()    # 1
        self.page_scan = ScanPage()              # 2
        self.page_output = OutputPage()          # 3
        self.page_dedup = DedupPage()            # 4
        self.page_model = ModelConfigPage()      # 5
        self.page_settings = SettingsPage()      # 6

        self.stack.addWidget(self.page_quick)
        self.stack.addWidget(self.page_manage)
        self.stack.addWidget(self.page_scan)
        self.stack.addWidget(self.page_output)
        self.stack.addWidget(self.page_dedup)
        self.stack.addWidget(self.page_model)
        self.stack.addWidget(self.page_settings)

        root_layout.addWidget(self.stack)

        # 信号连接
        self.page_scan.sig_log.connect(self.page_settings.append_log)
        self.page_scan.sig_status.connect(self.update_status)
        self.page_scan.sig_busy.connect(self.update_busy_state)
        if hasattr(self.page_output, 'sig_path_changed'):
            self.page_output.sig_path_changed.connect(self.on_output_path_changed)
        self.page_manage.sig_settings_changed.connect(self.page_quick.load_data)

    @Slot(int)
    def on_nav_clicked(self, idx):
        self.stack.setCurrentIndex(idx)
        if idx == 0:
            self.page_quick.load_data()
        elif idx == 1:
            self.page_manage.load_data()

    def show_about(self):
        AboutDialog(self).exec()

    def check_first_run(self):
        if self.config.getboolean('Settings', 'is_first_run', fallback=True):
            self.show_welcome_dialog(modal=True)

    def show_welcome_dialog(self, modal=False):
        welcome = WelcomeDialog(self)
        if modal:
            welcome.exec()
        else:
            welcome.show()
        if welcome.chk_no_show.isChecked() and self.config.getboolean('Settings', 'is_first_run', fallback=True):
            self.config['Settings']['is_first_run'] = 'false'
            backend.save_config(self.config)

    @Slot(str)
    def update_status(self, msg):
        self.status_label.setText(" " + msg)

    @Slot(bool)
    def update_busy_state(self, is_busy):
        self.progress.setVisible(is_busy)

    @Slot(str)
    def on_output_path_changed(self, path):
        if hasattr(self, 'page_scan'):
            self.page_scan.update_path_hint(path)

    def restore_geometry(self):
        geo = self.config.get('Settings', 'window_geometry', fallback='')
        try:
            w, h, x, y = map(int, re.split(r'[x+]', geo))
            self.resize(QSize(w, h))
            self.move(x, y)
        except Exception:
            self.resize(950, 700)

    def closeEvent(self, e):
        self.page_scan.save_state()
        self.page_output.save_state()
        geo = self.geometry()
        self.config['Settings']['window_geometry'] = f"{geo.width()}x{geo.height()}+{geo.x()}+{geo.y()}"
        backend.save_config(self.config)
        e.accept()
