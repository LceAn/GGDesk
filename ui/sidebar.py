from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QPushButton, QButtonGroup,
    QFrame, QStyle, QSizePolicy
)
from PySide6.QtCore import Qt, Signal, Slot
from .widgets import NavButton, ClickableLabel  # 导入刚才拆分的控件


class Sidebar(QWidget):
    # 定义信号，让主窗口知道发生了什么，而不是直接操作主窗口
    page_changed = Signal(int)  # 切换页面请求 (index)
    about_requested = Signal()  # 点击关于请求

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("sidebar")
        self.setFixedWidth(220)  # 初始宽度

        self.nav_btns = []  # 存储按钮引用以便折叠
        self.nav_labels = []  # 存储标题引用以便隐藏

        self.build_ui()

    def build_ui(self):
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(10, 10, 10, 10)
        self.layout.setSpacing(5)

        # 1. 汉堡菜单 (Toggle)
        self.btn_toggle = QPushButton("☰ GGDesk")
        self.btn_toggle.setObjectName("navButton")
        self.btn_toggle.setStyleSheet(
            "font-weight: bold; font-size: 12pt; text-align: left; border: none; padding-left: 15px;")
        self.btn_toggle.clicked.connect(self.toggle_sidebar)
        self.layout.addWidget(self.btn_toggle)
        self.layout.addSpacing(10)

        # 2. 导航组
        self.nav_group = QButtonGroup(self)
        self.nav_group.setExclusive(True)
        self.nav_group.idClicked.connect(self.page_changed.emit)  # 转发信号

        # --- 菜单定义 ---
        self.add_category(" 快捷启动")
        self.add_nav_btn("  快捷启动", QStyle.StandardPixmap.SP_DesktopIcon, 0)
        self.add_nav_btn("  启动管理", QStyle.StandardPixmap.SP_FileDialogListView, 1)

        self.layout.addSpacing(15)
        self.add_category(" 工具箱")
        self.add_nav_btn("  扫描程序", QStyle.StandardPixmap.SP_ComputerIcon, 2)
        self.add_nav_btn("  生成路径", QStyle.StandardPixmap.SP_DirIcon, 3)
        self.add_nav_btn("  清理去重", QStyle.StandardPixmap.SP_TrashIcon, 4)  # Beta 9.0

        self.add_category(" 软件设置")
        self.add_nav_btn("  模型配置", QStyle.StandardPixmap.SP_DriveNetIcon, 5)
        self.add_nav_btn("  系统设置", QStyle.StandardPixmap.SP_FileDialogDetailedView, 6)

        self.layout.addStretch(1)

        # 3. 底部信息
        self.line = QFrame()
        self.line.setFrameShape(QFrame.Shape.HLine)
        self.line.setFrameShadow(QFrame.Shadow.Sunken)
        self.line.setStyleSheet("border-color: #444444;")
        self.layout.addWidget(self.line)
        self.layout.addSpacing(10)

        self.lbl_ver = ClickableLabel("Beta 9.3")
        self.lbl_ver.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_ver.setStyleSheet("color: #888888; font-size: 10pt; font-weight: bold;")
        self.lbl_ver.clicked.connect(self.about_requested.emit)
        self.layout.addWidget(self.lbl_ver)

        self.auth_lbl = ClickableLabel("By LceAn")
        self.auth_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.auth_lbl.setStyleSheet("color: #666666; font-size: 9pt; font-family: 'Segoe UI';")
        self.auth_lbl.clicked.connect(self.about_requested.emit)
        self.layout.addWidget(self.auth_lbl)

        self.layout.addSpacing(10)

    # --- 辅助构建函数 ---
    def add_category(self, title):
        lbl = QLabel(title)
        lbl.setObjectName("navCategory")
        lbl.setStyleSheet("color: #888; font-size: 9pt; margin-top: 10px; margin-bottom: 5px; margin-left: 5px;")
        self.layout.addWidget(lbl)
        self.nav_labels.append(lbl)

    def add_nav_btn(self, text, icon, idx):
        btn = NavButton(text, icon)
        self.nav_group.addButton(btn, idx)
        self.layout.addWidget(btn)
        self.nav_btns.append(btn)
        # 默认选中第一个
        if idx == 0: btn.setChecked(True)

    # --- 折叠逻辑 (封装在内部) ---
    def toggle_sidebar(self):
        is_collapsed = self.width() < 100
        target_width = 220 if is_collapsed else 60
        self.setFixedWidth(target_width)

        # 处理按钮文字和样式
        for btn in self.nav_btns:
            btn.setText(btn.full_text if is_collapsed else "")
            btn.setToolTip("" if is_collapsed else btn.full_text)
            if not is_collapsed:
                btn.setStyleSheet("text-align: center; padding: 10px;")
            else:
                btn.setStyleSheet("text-align: left; padding: 12px 15px;")

        # 处理标签显隐
        visible = is_collapsed
        for lbl in self.nav_labels: lbl.setVisible(visible)

        self.line.setVisible(visible)
        self.lbl_ver.setVisible(visible)
        self.auth_lbl.setVisible(visible)

        self.btn_toggle.setText("☰ GGDesk" if visible else "☰")
        if not is_collapsed:
            self.btn_toggle.setStyleSheet("text-align: center; border: none; font-size: 14pt;")
        else:
            self.btn_toggle.setStyleSheet(
                "text-align: left; font-weight: bold; font-size: 12pt; border: none; padding-left: 15px;")