from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QLabel,
    QPushButton, QButtonGroup, QStackedWidget, QStatusBar, QProgressBar,
    QFrame, QDialog
)
from PySide6.QtCore import Qt, QSize, Slot, QUrl, Signal
from PySide6.QtGui import QDesktopServices, QCursor
import re
import scanner_backend as backend

# 导入各个页面
from .page_scan import ScanPage
from .page_output import OutputPage
from .page_rules import RulesPage
from .page_settings import SettingsPage


# --- 关于弹窗 ---
class AboutDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("关于 GGDesk Shortcut Scanner")
        self.setFixedSize(400, 250)

        # 【Beta 5.3.2 修复】 显式设置标志：是对话框 + 有关闭按钮
        # 这样既去掉了问号，又保证了 X 按钮可用
        self.setWindowFlags(Qt.Dialog | Qt.WindowCloseButtonHint)

        layout = QVBoxLayout(self);
        layout.setSpacing(15);
        layout.setContentsMargins(30, 30, 30, 30)

        lbl_title = QLabel("GGDesk Shortcut Scanner")
        lbl_title.setStyleSheet("font-size: 16pt; font-weight: bold; color: #0078D7;")
        lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(lbl_title)

        lbl_ver = QLabel("Version: Beta 5.3.2")
        lbl_ver.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(lbl_ver)

        btn_gh = QPushButton("🔗 GitHub 仓库");
        btn_gh.setCursor(Qt.PointingHandCursor)
        btn_gh.clicked.connect(lambda: QDesktopServices.openUrl(QUrl("https://github.com/LceAn/GGDesk")))

        btn_auth = QPushButton("👤 开发者主页 (LceAn)");
        btn_auth.setCursor(Qt.PointingHandCursor)
        btn_auth.clicked.connect(lambda: QDesktopServices.openUrl(QUrl("https://github.com/LceAn")))

        layout.addWidget(btn_gh);
        layout.addWidget(btn_auth)
        layout.addStretch()


# 可点击的 Label
class ClickableLabel(QLabel):
    clicked = Signal()

    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setCursor(Qt.PointingHandCursor)

    def mousePressEvent(self, event): self.clicked.emit()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("快捷方式扫描器 (Beta 5.3.2)")
        self.config = backend.load_config()

        self.build_ui()
        self.setup_statusbar()
        self.restore_geometry()

        # 初始化路径提示
        if hasattr(self, 'page_output'):
            self.on_output_path_changed(self.page_output.out_edit.text())

        self.page_settings.append_log("系统已就绪")

    def setup_statusbar(self):
        self.status_bar = QStatusBar();
        self.setStatusBar(self.status_bar)
        self.status_label = QLabel("就绪");
        self.status_bar.addWidget(self.status_label)
        self.progress = QProgressBar();
        self.progress.setMaximumWidth(150);
        self.progress.setVisible(False)
        self.progress.setRange(0, 0);
        self.status_bar.addPermanentWidget(self.progress)

    def build_ui(self):
        main_widget = QWidget();
        self.setCentralWidget(main_widget)
        root_layout = QHBoxLayout(main_widget);
        root_layout.setContentsMargins(0, 0, 0, 0);
        root_layout.setSpacing(0)

        # Sidebar
        sidebar = QWidget();
        sidebar.setObjectName("sidebar");
        sidebar.setFixedWidth(220)
        sb_layout = QVBoxLayout(sidebar);
        sb_layout.setContentsMargins(10, 20, 10, 20);
        sb_layout.setSpacing(8)
        self.nav_group = QButtonGroup(self);
        self.nav_group.setExclusive(True)

        def add_nav(text, icon_enum, id):
            btn = QPushButton(text);
            btn.setObjectName("navButton");
            btn.setCheckable(True)
            btn.setIcon(self.style().standardIcon(icon_enum));
            btn.setIconSize(QSize(20, 20))
            self.nav_group.addButton(btn, id);
            sb_layout.addWidget(btn);
            return btn

        sb_layout.addWidget(QLabel(" 导航菜单"));
        sb_layout.addSpacing(5)
        from PySide6.QtWidgets import QStyle
        add_nav("  扫描程序", QStyle.StandardPixmap.SP_ComputerIcon, 0).setChecked(True)
        add_nav("  生成路径", QStyle.StandardPixmap.SP_DirIcon, 1)
        add_nav("  规则管理", QStyle.StandardPixmap.SP_FileDialogListView, 2)
        add_nav("  系统设置", QStyle.StandardPixmap.SP_FileDialogDetailedView, 3)

        sb_layout.addStretch(1)
        line = QFrame();
        line.setFrameShape(QFrame.Shape.HLine);
        line.setFrameShadow(QFrame.Shadow.Sunken)
        line.setStyleSheet("border-color: #444444;");
        sb_layout.addWidget(line);
        sb_layout.addSpacing(10)

        # 可点击的归属信息
        ver_lbl = ClickableLabel("Beta 5.3.2");
        ver_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ver_lbl.setStyleSheet("color: #888888; font-size: 10pt; font-weight: bold;")
        ver_lbl.clicked.connect(self.show_about)

        auth_lbl = ClickableLabel("By LceAn");
        auth_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        auth_lbl.setStyleSheet("color: #666666; font-size: 9pt; font-family: 'Segoe UI';")
        auth_lbl.clicked.connect(self.show_about)

        sb_layout.addWidget(ver_lbl);
        sb_layout.addWidget(auth_lbl);
        sb_layout.addSpacing(10)
        root_layout.addWidget(sidebar)

        # Content Pages
        self.stack = QStackedWidget();
        self.stack.setObjectName("mainArea")

        self.page_scan = ScanPage()
        self.page_output = OutputPage()
        self.page_rules = RulesPage()
        self.page_settings = SettingsPage()

        self.stack.addWidget(self.page_scan)
        self.stack.addWidget(self.page_output)
        self.stack.addWidget(self.page_rules)
        self.stack.addWidget(self.page_settings)

        root_layout.addWidget(self.stack)
        self.nav_group.idClicked.connect(self.stack.setCurrentIndex)

        self.page_scan.sig_log.connect(self.page_settings.append_log)
        self.page_scan.sig_status.connect(self.update_status)
        self.page_output.sig_path_changed.connect(self.on_output_path_changed)

    def show_about(self):
        AboutDialog(self).exec()

    @Slot(str)
    def update_status(self, msg):
        self.status_label.setText(msg)
        self.progress.setVisible("扫描" in msg)

    @Slot(str)
    def on_output_path_changed(self, path):
        self.page_scan.update_path_hint(path)

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