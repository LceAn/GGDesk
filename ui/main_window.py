from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QLabel,
    QPushButton, QButtonGroup, QStackedWidget, QStatusBar, QProgressBar,
    QFrame, QDialog, QStyle, QSizePolicy, QApplication
)
from PySide6.QtCore import Qt, QSize, Slot, QUrl, Signal
from PySide6.QtGui import QDesktopServices, QCursor, QIcon
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
from .dialog_welcome import WelcomeDialog
from .dialog_about import AboutDialog


# 【修复】 已移除 page_rules 导入，因为它是弹窗 (RulesDialog)，不由主窗口管理

class ClickableLabel(QLabel):
    clicked = Signal()

    def __init__(self, text, parent=None):
        super().__init__(text, parent);
        self.setCursor(Qt.PointingHandCursor)

    def mousePressEvent(self, event): self.clicked.emit()


class NavButton(QPushButton):
    def __init__(self, text, icon_enum, parent=None):
        super().__init__(text, parent)
        self.full_text = text;
        self.setObjectName("navButton");
        self.setCheckable(True)
        self.setIcon(QApplication.style().standardIcon(icon_enum));
        self.setIconSize(QSize(20, 20))


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("GGDesk Beta 9.4.1")
        self.config = backend.load_config()
        backend.init_databases()

        self.build_ui()
        self.setup_statusbar()
        self.restore_geometry()

        if hasattr(self, 'page_output'): self.on_output_path_changed(self.page_output.out_edit.text())
        self.check_first_run()

    def setup_statusbar(self):
        self.status_bar = QStatusBar();
        self.setStatusBar(self.status_bar)
        self.status_bar.setStyleSheet("""
            QStatusBar { background-color: #FFFFFF; border-top: 1px solid #E5E5E5; min-height: 28px; color: #666666; }
            QStatusBar::item { border: none; }
        """)
        self.status_label = QLabel(" 就绪");
        self.status_label.setStyleSheet("padding-left: 5px;")
        self.status_bar.addWidget(self.status_label, 1)
        self.progress = QProgressBar();
        self.progress.setFixedWidth(150);
        self.progress.setFixedHeight(4);
        self.progress.setTextVisible(False)
        self.progress.setStyleSheet("""
            QProgressBar { background-color: #F0F0F0; border: none; border-radius: 2px; }
            QProgressBar::chunk { background-color: #0078D7; border-radius: 2px; }
        """)
        self.progress.setVisible(False);
        self.progress.setRange(0, 0)
        self.status_bar.addPermanentWidget(self.progress)

    def build_ui(self):
        main_widget = QWidget();
        self.setCentralWidget(main_widget)
        root_layout = QHBoxLayout(main_widget);
        root_layout.setContentsMargins(0, 0, 0, 0);
        root_layout.setSpacing(0)

        # Sidebar
        self.sidebar = QWidget();
        self.sidebar.setObjectName("sidebar");
        self.sidebar.setFixedWidth(220)
        sb_layout = QVBoxLayout(self.sidebar);
        sb_layout.setContentsMargins(10, 10, 10, 10);
        sb_layout.setSpacing(5)

        self.btn_toggle = QPushButton("☰ GGDesk");
        self.btn_toggle.setObjectName("navButton")
        self.btn_toggle.setStyleSheet(
            "font-weight: bold; font-size: 12pt; text-align: left; border: none; padding-left: 15px;")
        self.btn_toggle.clicked.connect(self.toggle_sidebar);
        sb_layout.addWidget(self.btn_toggle);
        sb_layout.addSpacing(10)

        self.nav_group = QButtonGroup(self);
        self.nav_group.setExclusive(True)
        self.nav_btns = [];
        self.nav_labels = []

        def add_cat(title):
            lbl = QLabel(title);
            lbl.setObjectName("navCategory");
            lbl.setStyleSheet("color: #888; font-size: 9pt; margin-top: 10px; margin-bottom: 5px; margin-left: 5px;")
            sb_layout.addWidget(lbl);
            self.nav_labels.append(lbl);
            return lbl

        add_cat(" 快捷启动")
        self.nav_quick = self.add_nav_btn("  快捷启动", QStyle.StandardPixmap.SP_DesktopIcon, 0, sb_layout)
        self.nav_manage = self.add_nav_btn("  启动管理", QStyle.StandardPixmap.SP_FileDialogListView, 1, sb_layout)

        add_cat(" 工具箱")
        self.nav_scan = self.add_nav_btn("  扫描程序", QStyle.StandardPixmap.SP_ComputerIcon, 2, sb_layout)
        self.nav_dedup = self.add_nav_btn("  清理去重", QStyle.StandardPixmap.SP_TrashIcon, 3, sb_layout)
        self.nav_out = self.add_nav_btn("  生成路径", QStyle.StandardPixmap.SP_DirIcon, 4, sb_layout)

        add_cat(" 软件设置")
        # 【修复】 移除了 nav_filter (规则管理)，因为它现在是 ScanPage 里的弹窗
        self.nav_model = self.add_nav_btn("  模型配置", QStyle.StandardPixmap.SP_DriveNetIcon, 5, sb_layout)
        self.nav_set = self.add_nav_btn("  系统设置", QStyle.StandardPixmap.SP_FileDialogDetailedView, 6, sb_layout)

        sb_layout.addStretch(1)

        self.line = QFrame();
        self.line.setFrameShape(QFrame.Shape.HLine);
        self.line.setFrameShadow(QFrame.Shadow.Sunken);
        self.line.setStyleSheet("border-color: #444444;");
        sb_layout.addWidget(self.line);
        sb_layout.addSpacing(10)
        self.lbl_ver = ClickableLabel("Beta 9.4.1");
        self.lbl_ver.setAlignment(Qt.AlignmentFlag.AlignCenter);
        self.lbl_ver.setStyleSheet("color: #888888; font-size: 10pt; font-weight: bold;");
        self.lbl_ver.clicked.connect(self.show_about);
        sb_layout.addWidget(self.lbl_ver)
        self.auth_lbl = ClickableLabel("By LceAn");
        self.auth_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter);
        self.auth_lbl.setStyleSheet("color: #666666; font-size: 9pt; font-family: 'Segoe UI';");
        self.auth_lbl.clicked.connect(self.show_about);
        sb_layout.addWidget(self.auth_lbl)
        sb_layout.addSpacing(5);
        root_layout.addWidget(self.sidebar)

        # Pages
        self.stack = QStackedWidget();
        self.stack.setObjectName("mainArea")

        # 必须与 ID 对应
        self.page_quick = QuickLaunchPage()  # 0
        self.page_manage = LaunchManagePage()  # 1
        self.page_scan = ScanPage()  # 2
        self.page_dedup = DedupPage()  # 3
        self.page_output = OutputPage()  # 4
        # 移除了 page_rules
        self.page_model = ModelConfigPage()  # 5
        self.page_settings = SettingsPage()  # 6

        self.stack.addWidget(self.page_quick)
        self.stack.addWidget(self.page_manage)
        self.stack.addWidget(self.page_scan)
        self.stack.addWidget(self.page_dedup)
        self.stack.addWidget(self.page_output)
        self.stack.addWidget(self.page_model)
        self.stack.addWidget(self.page_settings)

        root_layout.addWidget(self.stack)
        self.nav_group.idClicked.connect(self.on_nav_clicked)
        self.nav_quick.setChecked(True);
        self.stack.setCurrentIndex(0)

        self.page_scan.sig_log.connect(self.page_settings.append_log)
        self.page_scan.sig_status.connect(self.update_status)
        self.page_scan.sig_busy.connect(self.update_busy_state)
        if hasattr(self.page_output, 'sig_path_changed'): self.page_output.sig_path_changed.connect(
            self.on_output_path_changed)
        self.page_manage.sig_settings_changed.connect(self.page_quick.load_data)

    def add_nav_btn(self, text, icon, idx, layout):
        btn = NavButton(text, icon)
        self.nav_group.addButton(btn, idx)
        layout.addWidget(btn)
        self.nav_btns.append(btn)
        return btn

    def toggle_sidebar(self):
        is_collapsed = self.sidebar.width() < 100
        target_width = 220 if is_collapsed else 60
        self.sidebar.setFixedWidth(target_width)
        for btn in self.nav_btns:
            btn.setText(btn.full_text if is_collapsed else "")
            btn.setToolTip("" if is_collapsed else btn.full_text)
            if not is_collapsed:
                btn.setStyleSheet("text-align: center; padding: 10px;")
            else:
                btn.setStyleSheet("text-align: left; padding: 12px 15px;")
        visible = is_collapsed
        for lbl in self.nav_labels: lbl.setVisible(visible)
        self.line.setVisible(visible);
        self.lbl_ver.setVisible(visible);
        self.auth_lbl.setVisible(visible)
        self.btn_toggle.setText("☰ GGDesk" if visible else "☰")
        if not is_collapsed:
            self.btn_toggle.setStyleSheet("text-align: center; border: none; font-size: 14pt;")
        else:
            self.btn_toggle.setStyleSheet(
                "text-align: left; font-weight: bold; font-size: 12pt; border: none; padding-left: 15px;")

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
        if self.config.getboolean('Settings', 'is_first_run', fallback=True): self.show_welcome_dialog(modal=True)

    def show_welcome_dialog(self, modal=False):
        welcome = WelcomeDialog(self)
        if modal:
            welcome.exec()
        else:
            welcome.show()
        if welcome.chk_no_show.isChecked() and self.config.getboolean('Settings', 'is_first_run', fallback=True):
            self.config['Settings']['is_first_run'] = 'false';
            backend.save_config(self.config)

    @Slot(str)
    def update_status(self, msg):
        self.status_label.setText(" " + msg)

    @Slot(bool)
    def update_busy_state(self, is_busy):
        self.progress.setVisible(is_busy)

    @Slot(str)
    def on_output_path_changed(self, path):
        if hasattr(self, 'page_scan'): self.page_scan.update_path_hint(path)

    def restore_geometry(self):
        geo = self.config.get('Settings', 'window_geometry', fallback='')
        try:
            w, h, x, y = map(int, re.split(r'[x+]', geo)); self.resize(QSize(w, h)); self.move(x, y)
        except:
            self.resize(950, 700)

    def closeEvent(self, e):
        self.page_scan.save_state();
        self.page_output.save_state()
        geo = self.geometry();
        self.config['Settings']['window_geometry'] = f"{geo.width()}x{geo.height()}+{geo.x()}+{geo.y()}"
        backend.save_config(self.config)
        e.accept()