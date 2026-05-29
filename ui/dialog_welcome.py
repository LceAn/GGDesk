# ui/dialog_welcome.py
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QStackedWidget, QWidget, QCheckBox, QFrame, QSizePolicy
)
from PySide6.QtCore import Qt, QPropertyAnimation, QRect
from PySide6.QtGui import QFont, QColor, QPalette


class WelcomeDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("欢迎使用 GGDesk")
        self.setFixedSize(700, 500)  # 固定大小，更易控制布局
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self.setStyleSheet("""
            QDialog {
                background-color: #f0f4f8;
            }
            #pageContent {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, 
                                            stop:0 #e0f2f7, stop:1 #d1e8ef);
                border-radius: 15px;
                margin: 15px;
                padding: 20px;
            }
            QLabel#title {
                font-size: 32pt; 
                font-weight: bold; 
                color: #2c3e50;
                margin-bottom: 10px;
            }
            QLabel#subtitle {
                font-size: 16pt; 
                color: #3498db;
                margin-bottom: 30px;
            }
            QLabel#content {
                font-size: 11pt; 
                color: #555; 
                line-height: 1.6;
                padding: 0 30px;
            }
            QCheckBox {
                font-size: 10pt;
                color: #666;
            }
            QPushButton {
                padding: 8px 20px;
                border-radius: 8px;
                font-size: 10pt;
                font-weight: bold;
                background-color: #cccccc;
                color: #333;
                border: none;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #bbbbbb;
            }
            QPushButton#primaryButton {
                background-color: #3498db;
                color: white;
            }
            QPushButton#primaryButton:hover {
                background-color: #2980b9;
            }
            QPushButton:disabled {
                background-color: #e0e0e0;
                color: #999;
            }
        """)

        self.build_ui()
        self.current_page_idx = 0
        self.update_navigation_buttons()

    def build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)  # 对话框本身的边距设为0

        # 1. 内容区 (Stacked Widget) - 使用 QFrame 作为背景
        self.content_frame = QFrame()
        self.content_frame.setObjectName("pageContent")  # 用于CSS样式
        frame_layout = QVBoxLayout(self.content_frame)
        frame_layout.setContentsMargins(0, 0, 0, 0)  # frame内部边距也设为0

        self.stack = QStackedWidget()

        # Page 1: 欢迎
        self.page1 = self.create_page(
            "👋",  # 表情符号图标
            "欢迎来到 GGDesk",
            "您的智能桌面整理专家。",
            "GGDesk 可以帮您扫描电脑中散落的免安装程序、开始菜单应用和 UWP 应用，\n"
            "并通过智能算法自动生成整洁的快捷方式，让桌面管理更高效、更智能。"
        )

        # Page 2: 功能介绍
        self.page2 = self.create_page(
            "🚀",
            "核心功能概览",
            "不仅仅是创建快捷方式。",
            "• 🛡️ **规则引擎**：精准过滤卸载程序、系统组件和无关文件。\n"
            "• 🧠 **智能识别**：自动判断软件根目录，并推荐最合适的启动项。\n"
            "• 📂 **多源合一**：统一管理来自本地、开始菜单和微软商店的应用入口。\n"
            "• ✨ **现代体验**：简洁美观的界面设计，支持主题切换。"
        )

        # Page 3: 开始使用
        self.page3 = self.create_page(
            "✨",
            "准备就绪",
            "开始您的 GGDesk 旅程吧！",
            "点击下方的“开始体验”按钮，\n"
            "即可进入主界面，开始探索 GGDesk 的强大功能。\n"
            "我们致力于为您带来前所未有的桌面管理体验！"
        )

        self.stack.addWidget(self.page1)
        self.stack.addWidget(self.page2)
        self.stack.addWidget(self.page3)

        frame_layout.addWidget(self.stack)  # StackedWidget 放到 Frame 里面
        main_layout.addWidget(self.content_frame)  # Frame 放到主布局里面

        # 2. 底部控制栏
        bottom_bar = QFrame()
        bottom_bar.setStyleSheet("""
            background-color: #ffffff;
            border-top: 1px solid #e0e0e0;
            border-bottom-left-radius: 15px;
            border-bottom-right-radius: 15px;
        """)
        bar_layout = QHBoxLayout(bottom_bar)
        bar_layout.setContentsMargins(30, 15, 30, 15)  # 调整边距

        self.chk_no_show = QCheckBox("下次不再显示")
        self.chk_no_show.setChecked(True)  # 默认勾选

        self.btn_prev = QPushButton("上一步")
        self.btn_next = QPushButton("下一步")
        self.btn_next.setObjectName("primaryButton")

        self.btn_prev.clicked.connect(self.prev_page)
        self.btn_next.clicked.connect(self.next_page)

        bar_layout.addWidget(self.chk_no_show)
        bar_layout.addStretch()
        bar_layout.addWidget(self.btn_prev)
        bar_layout.addWidget(self.btn_next)

        main_layout.addWidget(bottom_bar)  # 底部控制栏也放到主布局

    def create_page(self, icon_emoji, title, subtitle, content):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(15)  # 调整组件间距

        lbl_icon = QLabel(icon_emoji)
        lbl_icon.setStyleSheet("font-size: 60pt; margin-bottom: 20px;")  # 大图标
        lbl_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)

        lbl_title = QLabel(title)
        lbl_title.setObjectName("title")
        lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        lbl_sub = QLabel(subtitle)
        lbl_sub.setObjectName("subtitle")
        lbl_sub.setAlignment(Qt.AlignmentFlag.AlignCenter)

        lbl_content = QLabel(content)
        lbl_content.setObjectName("content")
        lbl_content.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_content.setWordWrap(True)  # 自动换行
        lbl_content.setTextFormat(Qt.TextFormat.MarkdownText)

        layout.addWidget(lbl_icon)
        layout.addWidget(lbl_title)
        layout.addWidget(lbl_sub)
        layout.addSpacing(20)  # 标题和内容之间增加一些间距
        layout.addWidget(lbl_content)
        layout.addStretch()
        return page

    def next_page(self):
        if self.current_page_idx < self.stack.count() - 1:
            self.current_page_idx += 1
            self.stack.setCurrentIndex(self.current_page_idx)
            self.update_navigation_buttons()
        else:
            self.accept()  # 关闭窗口

    def prev_page(self):
        if self.current_page_idx > 0:
            self.current_page_idx -= 1
            self.stack.setCurrentIndex(self.current_page_idx)
            self.update_navigation_buttons()

    def update_navigation_buttons(self):
        self.btn_prev.setEnabled(self.current_page_idx > 0)
        if self.current_page_idx == self.stack.count() - 1:
            self.btn_next.setText("开始体验")
            self.btn_next.setObjectName("primaryButton")
        else:
            self.btn_next.setText("下一步")
            self.btn_next.setObjectName("primaryButton")  # 确保样式不变