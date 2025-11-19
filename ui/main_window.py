from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QLabel,
    QPushButton, QButtonGroup, QStackedWidget, QStatusBar, QProgressBar,
    QFrame  # 新增引用
)
from PySide6.QtCore import Qt, QSize, Slot
import re
import scanner_backend as backend

# 导入各个页面
from .page_scan import ScanPage
from .page_output import OutputPage
from .page_filter import FilterPage
from .page_settings import SettingsPage


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("快捷方式扫描器 (Beta 4.5 Experience)")
        self.config = backend.load_config()

        self.build_ui()
        self.setup_statusbar()
        self.restore_geometry()

        self.on_output_path_changed(self.page_output.out_edit.text())
        self.page_settings.append_log("系统已就绪 (体验优化版)")

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
        add_nav("  过滤规则", QStyle.StandardPixmap.SP_MessageBoxWarning, 2)
        add_nav("  系统设置", QStyle.StandardPixmap.SP_FileDialogDetailedView, 3)

        # 【Beta 4.5 修复】 使用 addStretch(1) 将下方内容顶到底部
        sb_layout.addStretch(1)

        # 分隔线
        line = QFrame();
        line.setFrameShape(QFrame.Shape.HLine);
        line.setFrameShadow(QFrame.Shadow.Sunken)
        line.setStyleSheet("border-color: #444444;")  # 弱化线条
        sb_layout.addWidget(line)
        sb_layout.addSpacing(10)

        # 归属信息 (增加底部边距)
        ver_lbl = QLabel("Beta 4.5");
        ver_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ver_lbl.setStyleSheet("color: #888888; font-size: 10pt; font-weight: bold;")

        auth_lbl = QLabel("By LceAn");
        auth_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        auth_lbl.setStyleSheet("color: #666666; font-size: 9pt; font-family: 'Segoe UI';")  # 稍微调大字体

        sb_layout.addWidget(ver_lbl)
        sb_layout.addWidget(auth_lbl)

        # 额外的底部留白，防止贴底
        sb_layout.addSpacing(10)

        root_layout.addWidget(sidebar)

        # Content Pages
        self.stack = QStackedWidget();
        self.stack.setObjectName("mainArea")

        self.page_scan = ScanPage()
        self.page_output = OutputPage()
        self.page_filter = FilterPage()
        self.page_settings = SettingsPage()

        self.stack.addWidget(self.page_scan)
        self.stack.addWidget(self.page_output)
        self.stack.addWidget(self.page_filter)
        self.stack.addWidget(self.page_settings)

        root_layout.addWidget(self.stack)
        self.nav_group.idClicked.connect(self.stack.setCurrentIndex)

        # Signals
        self.page_scan.sig_log.connect(self.page_settings.append_log)
        self.page_scan.sig_status.connect(self.update_status)
        self.page_output.sig_path_changed.connect(self.on_output_path_changed)

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
            w, h, x, y = map(int, re.split(r'[x+]', geo))
            self.resize(QSize(w, h));
            self.move(x, y)
        except:
            self.resize(950, 700)

    def closeEvent(self, e):
        self.page_scan.save_state()
        self.page_output.save_state()
        geo = self.geometry();
        self.config['Settings']['window_geometry'] = f"{geo.width()}x{geo.height()}+{geo.x()}+{geo.y()}"
        backend.save_config(self.config)
        e.accept()