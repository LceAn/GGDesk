import sys
import os
import re

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QFrame, QFileDialog, QLineEdit, QLabel, QTreeWidget,
    QTreeWidgetItem, QHeaderView, QDialog, QDialogButtonBox,
    QMessageBox, QTextEdit, QStackedWidget, QButtonGroup, QComboBox
)
from PySide6.QtCore import Qt, QSize, QObject, Signal, Slot, QThread
from PySide6.QtGui import QCloseEvent

# 导入我们的后端
import scanner_backend as backend

# --- v8.4 样式表 ---

# 【新】 亮色主题
LIGHT_STYLESHEET = """
QWidget {
    font-family: "Microsoft YaHei UI", "Segoe UI", Arial, sans-serif;
    font-size: 10pt;
    color: #000000; /* 黑色文字 */
}
QMainWindow { background-color: #F0F0F0; } /* 窗口亮灰 */

/* 侧边栏 */
QWidget[objectName="sidebar"] {
    background-color: #E0E0E0; /* 侧边栏稍暗 */
    border-right: 1px solid #C0C0C0;
}
QLabel[objectName="navHeader"] {
    color: #555555; font-size: 9pt; padding: 10px 10px 5px 10px;
    font-weight: bold; background-color: transparent;
}
QPushButton[objectName="navButton"] {
    background-color: transparent; color: #333333; border: none;
    padding: 10px; text-align: left; border-radius: 4px; margin: 5px 10px;
}
QPushButton[objectName="navButton"]:hover { background-color: #D0D0D0; }
QPushButton[objectName="navButton"]:checked {
    background-color: #0078D7; color: #FFFFFF; font-weight: bold;
}

/* 主内容区 */
QWidget[objectName="mainArea"] { background-color: #F0F0F0; }

/* 通用控件 */
QLabel { background-color: transparent; color: #444444; font-size: 9pt; }
QLabel[objectName="headerLabel"] {
    color: #000000; font-size: 11pt; font-weight: bold;
}
QPushButton {
    background-color: #E0E0E0; color: #000000; border: 1px solid #B0B0B0;
    padding: 8px 16px; border-radius: 4px; min-height: 20px;
}
QPushButton:hover { background-color: #D0D0D0; }
QPushButton:pressed { background-color: #C0C0C0; }
QPushButton:disabled { background-color: #E5E5E5; color: #999999; }

QPushButton[objectName="primaryButton"] {
    background-color: #0078D7; color: #FFFFFF; font-weight: bold;
    border: 1px solid #005A9E;
}
QPushButton[objectName="primaryButton"]:hover { background-color: #0088F0; }
QPushButton[objectName="primaryButton"]:pressed { background-color: #005A9E; }

QLineEdit, QTextEdit, QComboBox {
    background-color: #FFFFFF; color: #000000; border: 1px solid #B0B0B0;
    border-radius: 4px; padding: 5px;
}
QComboBox QAbstractItemView { /* 下拉菜单样式 */
    background-color: #FFFFFF; border: 1px solid #B0B0B0;
}

QTextEdit[objectName="logArea"] {
    font-family: "Consolas", "Courier New", monospace;
    background-color: #F8F8F8;
    color: #111111;
}
QTreeWidget {
    background-color: #FFFFFF; border: 1px solid #B0B0B0;
    border-radius: 4px; alternate-background-color: #F0F0F0;
}
QTreeWidget::item { padding: 5px; color: #000000; }
QTreeWidget::item:selected { background-color: #0078D7; color: #FFFFFF; }
QTreeWidget::item:hover { background-color: #E0E0E0; }

QHeaderView::section {
    background-color: #E0E0E0; color: #000000; padding: 5px;
    border: 1px solid #C0C0C0; font-weight: bold;
}
QFrame[frameShape="4"] { border: 1px solid #D0D0D0; } /* HLine */

/* 滚动条 */
QScrollBar:vertical { border: none; background: #F0F0F0; width: 14px; margin: 14px 0 14px 0; }
QScrollBar::handle:vertical { background: #C0C0C0; min-height: 20px; border-radius: 7px; }
QScrollBar::handle:vertical:hover { background: #B0B0B0; }
QScrollBar:horizontal { border: none; background: #F0F0F0; height: 14px; margin: 0 14px 0 14px; }
QScrollBar::handle:horizontal { background: #C0C0C0; min-width: 20px; border-radius: 7px; }
QScrollBar::handle:horizontal:hover { background: #B0B0B0; }
"""

# 【暗黑】主题 (v8.3)
DARK_STYLESHEET = """
QWidget {
    font-family: "Microsoft YaHei UI", "Segoe UI", Arial, sans-serif;
    font-size: 10pt;
    color: #F0F0F0;
}
QMainWindow { background-color: #2B2B2B; }
/* 侧边栏 */
QWidget[objectName="sidebar"] {
    background-color: #202020;
    border-right: 1px solid #404040;
}
QLabel[objectName="navHeader"] {
    color: #AAAAAA; font-size: 9pt; padding: 10px 10px 5px 10px;
    font-weight: bold; background-color: transparent;
}
QPushButton[objectName="navButton"] {
    background-color: transparent; color: #D0D0D0; border: none;
    padding: 10px; text-align: left; border-radius: 4px; margin: 5px 10px;
}
QPushButton[objectName="navButton"]:hover { background-color: #3A3A3A; }
QPushButton[objectName="navButton"]:checked {
    background-color: #0078D7; color: #FFFFFF; font-weight: bold;
}
/* 主内容区 */
QWidget[objectName="mainArea"] { background-color: #2B2B2B; }
/* 通用控件 */
QLabel { background-color: transparent; color: #AAAAAA; font-size: 9pt; }
QLabel[objectName="headerLabel"] {
    color: #F0F0F0; font-size: 11pt; font-weight: bold;
}
QPushButton {
    background-color: #4A4A4A; color: #F0F0F0; border: 1px solid #5A5A5A;
    padding: 8px 16px; border-radius: 4px; min-height: 20px;
}
QPushButton:hover { background-color: #5A5A5A; }
QPushButton:pressed { background-color: #6A6A6A; }
QPushButton:disabled { background-color: #3A3A3A; color: #777777; }
QPushButton[objectName="primaryButton"] {
    background-color: #0078D7; color: #FFFFFF; font-weight: bold;
    border: 1px solid #005A9E;
}
QPushButton[objectName="primaryButton"]:hover { background-color: #0088F0; }
QPushButton[objectName="primaryButton"]:pressed { background-color: #005A9E; }
QLineEdit, QTextEdit, QComboBox {
    background-color: #252525; color: #F0F0F0; border: 1px solid #5A5A5A;
    border-radius: 4px; padding: 5px;
}
QComboBox QAbstractItemView {
    background-color: #252525; border: 1px solid #5A5A5A; color: #F0F0F0;
    selection-background-color: #0078D7;
}
QTextEdit[objectName="logArea"] {
    font-family: "Consolas", "Courier New", monospace;
    font-size: 9pt;
}
QTreeWidget {
    background-color: #252525; border: 1px solid #5A5A5A;
    border-radius: 4px; alternate-background-color: #2E2E2E;
}
QTreeWidget::item { padding: 5px; }
QTreeWidget::item:selected { background-color: #0078D7; color: #FFFFFF; }
QTreeWidget::item:hover { background-color: #3A3A3A; }
QHeaderView::section {
    background-color: #3A3A3A; color: #F0F0F0; padding: 5px;
    border: 1px solid #5A5A5A; font-weight: bold;
}
QFrame[frameShape="4"] { border: 1px solid #4A4A4A; } /* HLine */
/* 滚动条 */
QScrollBar:vertical { border: none; background: #2B2B2B; width: 14px; margin: 14px 0 14px 0; }
QScrollBar::handle:vertical { background: #4A4A4A; min-height: 20px; border-radius: 7px; }
QScrollBar::handle:vertical:hover { background: #5A5A5A; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 14px; border: none; background: #3A3A3A; }
QScrollBar::sub-line:vertical:pressed, QScrollBar::add-line:vertical:pressed { background: #5A5A5A; }
QScrollBar:horizontal { border: none; background: #2B2B2B; height: 14px; margin: 0 14px 0 14px; }
QScrollBar::handle:horizontal { background: #4A4A4A; min-width: 20px; border-radius: 7px; }
QScrollBar::handle:horizontal:hover { background: #5A5A5A; }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 14px; border: none; background: #3A3A3A; }
QScrollBar::sub-line:horizontal:pressed, QScrollBar::add-line:horizontal:pressed { background: #5A5A5A; }
"""


# --- 【新】v8.4 多线程扫描器 ---
class ScanWorker(QObject):
    """
    在工作线程中运行扫描器
    """
    # 信号: (扫描结果列表), (日志消息)
    finished = Signal(list)
    log = Signal(str)

    def __init__(self, scan_path, blocklist):
        super().__init__()
        self.scan_path = scan_path
        self.blocklist = blocklist
        self.is_running = True

    @Slot()
    def run(self):
        """
        线程入口点。调用后端函数并传递 log 信号
        """
        try:
            # 将 self.log (信号) 作为 log_callback 传递给后端
            programs = backend.discover_programs(self.scan_path, self.blocklist, self.log.emit)
            self.finished.emit(programs)
        except Exception as e:
            self.log.emit(f"--- 扫描线程发生严重错误 ---")
            self.log.emit(str(e))
            self.finished.emit([])


# --- 详情弹窗 (Stage 2) (与 v8.3 完全相同) ---
class RefineWindow(QDialog):
    def __init__(self, parent, program_data):
        super().__init__(parent)
        self.setWindowTitle(f"详情: {program_data['name']}")
        self.setMinimumSize(700, 500)
        self.setModal(True)

        self.program_data = program_data
        self.all_exes = program_data['all_exes']
        self.original_selection = set(program_data['selected_exes'])

        self.build_ui()
        self.populate_tree()
        self.pre_select_items()
        self.on_filter_changed()

    def build_ui(self):
        layout = QVBoxLayout(self)
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("筛选:"))
        self.filter_edit = QLineEdit()
        self.filter_edit.setPlaceholderText("按名称或路径筛选...")
        self.filter_edit.textChanged.connect(self.on_filter_changed)
        filter_layout.addWidget(self.filter_edit)
        layout.addLayout(filter_layout)
        self.tree = QTreeWidget()
        self.tree.setColumnCount(3)
        self.tree.setHeaderLabels(['程序名', '大小', '相对路径'])
        self.tree.setSelectionMode(QTreeWidget.SelectionMode.ExtendedSelection)
        self.tree.setSortingEnabled(True)
        header = self.tree.header()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.tree)
        btn_layout = QHBoxLayout()
        btn_all = QPushButton("全选 (可见)")
        btn_all.clicked.connect(self.select_all_visible)
        btn_none = QPushButton("全不选")
        btn_none.clicked.connect(self.select_none)
        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.button_box.accepted.connect(self.on_ok)
        self.button_box.rejected.connect(self.reject)
        btn_layout.addWidget(btn_all)
        btn_layout.addWidget(btn_none)
        btn_layout.addStretch()
        btn_layout.addWidget(self.button_box)
        layout.addLayout(btn_layout)

    def populate_tree(self):
        self.tree.setSortingEnabled(False)
        items = []
        for (full_path, file_name, size_bytes, relative_path) in self.all_exes:
            item = QTreeWidgetItem([file_name, "", relative_path])
            item.setData(0, Qt.ItemDataRole.UserRole, full_path)
            item.setData(1, Qt.ItemDataRole.UserRole, size_bytes)
            item.setData(1, Qt.ItemDataRole.DisplayRole, size_bytes)
            items.append(item)
        self.tree.addTopLevelItems(items)
        for item in items:
            size_mb = f"{item.data(1, Qt.ItemDataRole.UserRole) / (1024 * 1024):.2f} MB"
            item.setText(1, size_mb)
        self.tree.setSortingEnabled(True)

    def pre_select_items(self):
        for item in self.tree.findItems("", Qt.MatchFlag.MatchContains | Qt.MatchFlag.MatchRecursive, 0):
            full_path = item.data(0, Qt.ItemDataRole.UserRole)
            if full_path in self.original_selection:
                item.setSelected(True)

    def on_filter_changed(self, text=""):
        query = self.filter_edit.text().lower()
        for i in range(self.tree.topLevelItemCount()):
            item = self.tree.topLevelItem(i)
            name_match = query in item.text(0).lower()
            path_match = query in item.text(2).lower()
            item.setHidden(not (name_match or path_match))

    def select_all_visible(self):
        self.select_none()
        for i in range(self.tree.topLevelItemCount()):
            item = self.tree.topLevelItem(i)
            if not item.isHidden():
                item.setSelected(True)

    def select_none(self):
        self.tree.clearSelection()

    def on_ok(self):
        selected_paths = []
        for item in self.tree.selectedItems():
            selected_paths.append(item.data(0, Qt.ItemDataRole.UserRole))
        self.program_data['selected_exes'] = tuple(selected_paths)
        self.accept()


# --- 主窗口 (v8.4 架构) ---
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("快捷方式扫描器 (v8.4)")

        # --- 数据 ---
        self.config = backend.load_config()
        self.programs = []
        self.blocklist, msg_blocklist = backend.load_blocklist()

        # --- 线程 ---
        self.scan_thread = None
        self.scan_worker = None

        # --- UI ---
        self.build_ui()

        # --- 加载配置 ---
        self.log(f"程序已启动。{msg_blocklist}")
        geometry = self.config.get('Settings', 'window_geometry', fallback='900x700')
        try:
            w, h, x, y = map(int, re.split(r'[x+]', geometry))
            self.resize(QSize(w, h))
            self.move(x, y)
        except Exception:
            self.resize(QSize(900, 700))

        # 【新】v8.4 加载主题
        self.load_theme()

        # 【新】v8.4 加载自定义路径
        self.output_path_edit.setText(self.config.get('Settings', 'output_path', fallback=''))

    def build_ui(self):
        # 1. 根布局
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        root_layout = QHBoxLayout(main_widget)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # 2. 侧边栏
        sidebar = QWidget()
        sidebar.setObjectName("sidebar")
        sidebar.setMinimumWidth(180)
        sidebar.setMaximumWidth(180)

        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(0, 10, 0, 10)
        sidebar_layout.setSpacing(5)

        self.nav_group = QButtonGroup(self)
        self.nav_group.setExclusive(True)

        nav_header = QLabel("导航")
        nav_header.setObjectName("navHeader")

        self.nav_btn_scanner = QPushButton("程序扫描")
        self.nav_btn_scanner.setObjectName("navButton")
        self.nav_btn_scanner.setCheckable(True)

        self.nav_btn_settings = QPushButton("应用设置")
        self.nav_btn_settings.setObjectName("navButton")
        self.nav_btn_settings.setCheckable(True)

        self.nav_group.addButton(self.nav_btn_scanner, 0)
        self.nav_group.addButton(self.nav_btn_settings, 1)

        sidebar_layout.addWidget(nav_header)
        sidebar_layout.addWidget(self.nav_btn_scanner)
        sidebar_layout.addWidget(self.nav_btn_settings)
        sidebar_layout.addStretch()
        root_layout.addWidget(sidebar)

        # 3. 主内容区
        self.stack = QStackedWidget()
        self.stack.setObjectName("mainArea")

        self.scanner_view = self.create_scanner_view()  # 页面 1
        self.stack.addWidget(self.scanner_view)

        self.settings_view = self.create_settings_view()  # 页面 2
        self.stack.addWidget(self.settings_view)

        # 3c. 日志区
        log_widget = QWidget()
        log_widget.setObjectName("mainArea")
        log_widget.setMinimumHeight(150)
        log_widget.setMaximumHeight(200)
        log_layout = QVBoxLayout(log_widget)
        log_layout.setContentsMargins(15, 0, 15, 15)

        log_layout.addWidget(self.create_separator())
        log_layout.addWidget(QLabel("日志输出"))
        self.log_area = QTextEdit()
        self.log_area.setObjectName("logArea")
        self.log_area.setReadOnly(True)
        log_layout.addWidget(self.log_area)

        # 4. 组装
        main_content_and_log_layout = QVBoxLayout()
        main_content_and_log_layout.setContentsMargins(0, 0, 0, 0)
        main_content_and_log_layout.setSpacing(0)
        main_content_and_log_layout.addWidget(self.stack, 1)
        main_content_and_log_layout.addWidget(log_widget)

        root_layout.addLayout(main_content_and_log_layout, 1)

        # 5. 连接信号
        self.nav_group.idClicked.connect(self.stack.setCurrentIndex)
        self.nav_btn_scanner.setChecked(True)

    def create_separator(self):
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        return line

    # --- 页面 1: 程序扫描 (UI创建) ---
    def create_scanner_view(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)

        path_layout = QHBoxLayout()
        path_layout.addWidget(QLabel("扫描路径:"))
        self.path_edit = QLineEdit()
        self.path_edit.setReadOnly(True)
        self.path_edit.setText(self.config.get('Settings', 'last_scan_path', fallback=''))
        path_layout.addWidget(self.path_edit)
        self.btn_scan = QPushButton("选择目录...")
        self.btn_scan.clicked.connect(self.ask_scan_path)
        path_layout.addWidget(self.btn_scan)
        layout.addLayout(path_layout)

        layout.addWidget(self.create_separator())

        # 【新】v8.4 Req 1+2: 计数 + 优化文案
        header_layout = QHBoxLayout()
        header_layout.addWidget(QLabel("发现的程序"), 0, Qt.AlignmentFlag.AlignBottom)
        header_layout.addStretch()
        self.program_count_label = QLabel("总共: 0 个")
        header_layout.addWidget(self.program_count_label, 0, Qt.AlignmentFlag.AlignBottom)
        layout.addLayout(header_layout)

        self.tree = QTreeWidget()
        self.tree.setColumnCount(3)
        self.tree.setHeaderLabels(['发现的程序', '当前选择', '程序根目录'])
        self.tree.setSelectionMode(QTreeWidget.SelectionMode.SingleSelection)
        header = self.tree.header()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.tree.itemSelectionChanged.connect(self.on_program_select)
        layout.addWidget(self.tree, 1)

        # 【新】v8.4 Req 2: 优化文案
        self.btn_refine = QPushButton("修改所选程序...")
        self.btn_refine.setEnabled(False)
        self.btn_refine.clicked.connect(self.open_refine_window)
        layout.addWidget(self.btn_refine)

        layout.addWidget(self.create_separator())

        self.btn_create = QPushButton("生成所有快捷方式")
        self.btn_create.setObjectName("primaryButton")
        self.btn_create.setEnabled(False)
        self.btn_create.setMinimumHeight(35)
        self.btn_create.clicked.connect(self.generate_shortcuts)
        layout.addWidget(self.btn_create)

        return page

    # --- 页面 2: 应用设置 (UI创建) ---
    def create_settings_view(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)

        # 【新】v8.4 Req 4: 主题切换
        layout.addWidget(QLabel("外观设置"), 0, Qt.AlignmentFlag.AlignBottom)
        theme_layout = QHBoxLayout()
        theme_layout.addWidget(QLabel("应用主题:"))
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["暗黑模式", "明亮模式"])
        self.theme_combo.currentIndexChanged.connect(self.on_theme_changed)
        theme_layout.addWidget(self.theme_combo)
        theme_layout.addStretch()
        layout.addLayout(theme_layout)

        layout.addWidget(self.create_separator())

        # 【新】v8.4 Req 3: 自定义输出路径
        layout.addWidget(QLabel("功能设置"), 0, Qt.AlignmentFlag.AlignBottom)
        out_path_layout = QHBoxLayout()
        out_path_layout.addWidget(QLabel("快捷方式输出目录:"))
        self.output_path_edit = QLineEdit()
        self.output_path_edit.setPlaceholderText("默认为桌面 'MyTestShortcuts' 文件夹")
        out_path_layout.addWidget(self.output_path_edit)
        btn_browse_out = QPushButton("浏览...")
        btn_browse_out.clicked.connect(self.on_browse_output_path)
        out_path_layout.addWidget(btn_browse_out)
        layout.addLayout(out_path_layout)

        layout.addWidget(self.create_separator())

        # 黑名单管理
        layout.addWidget(QLabel("黑名单管理 (blocklist.txt)"), 0, Qt.AlignmentFlag.AlignBottom)
        layout.addWidget(QLabel("每行一个文件名 (不区分大小写)。保存后下次扫描生效。"))

        self.blocklist_edit = QTextEdit()
        self.blocklist_edit.setPlainText("\n".join(sorted(self.blocklist)))
        layout.addWidget(self.blocklist_edit, 1)  # 1 = 伸展因子

        self.btn_save_blocklist = QPushButton("保存黑名单")
        self.btn_save_blocklist.clicked.connect(self.on_save_blocklist)
        layout.addWidget(self.btn_save_blocklist, 0, Qt.AlignmentFlag.AlignLeft)

        layout.addStretch()
        return page

    # --- 日志槽 ---
    @Slot(str)
    def log(self, message):
        self.log_area.append(message)
        self.log_area.verticalScrollBar().setValue(self.log_area.verticalScrollBar().maximum())

    # --- 槽函数 (连接到 UI) ---

    def on_save_blocklist(self):
        new_list = set(self.blocklist_edit.toPlainText().split('\n'))
        self.blocklist = {item.lower() for item in new_list if item.strip()}

        success, msg = backend.save_blocklist(self.blocklist)
        if success:
            self.log(f"[+] 黑名单已保存。")
            QMessageBox.information(self, "成功", "黑名单已保存。")
        else:
            self.log(f"[!] {msg}")
            QMessageBox.critical(self, "保存失败", msg)

    # 【新】v8.4 Req 3: 浏览输出路径
    def on_browse_output_path(self):
        path = QFileDialog.getExistingDirectory(self, "选择快捷方式输出目录", self.output_path_edit.text())
        if path:
            self.output_path_edit.setText(path)

    # 【新】v8.4 Req 4: 切换主题
    def on_theme_changed(self, index):
        if index == 0:  # 暗黑
            self.config['Settings']['theme'] = 'dark'
            qApp.setStyleSheet(DARK_STYLESHEET)
        else:  # 明亮
            self.config['Settings']['theme'] = 'light'
            qApp.setStyleSheet(LIGHT_STYLESHEET)
        self.log(f"主题已切换为: {self.config['Settings']['theme']}")

    def load_theme(self):
        theme = self.config.get('Settings', 'theme', fallback='dark')
        if theme == 'light':
            self.theme_combo.setCurrentIndex(1)
            qApp.setStyleSheet(LIGHT_STYLESHEET)
        else:
            self.theme_combo.setCurrentIndex(0)
            qApp.setStyleSheet(DARK_STYLESHEET)

    # 【新】v8.4 多线程扫描
    def ask_scan_path(self):
        # 检查是否已在扫描
        if self.scan_thread is not None and self.scan_thread.isRunning():
            self.log("[!] 扫描已在进行中，请稍候...")
            return

        initial_dir = self.config.get('Settings', 'last_scan_path', fallback=None)
        path_to_scan = QFileDialog.getExistingDirectory(self, "选择扫描目录", initial_dir)
        if not path_to_scan:
            self.log("[提示] 用户取消了目录选择。")
            return
        self.path_edit.setText(path_to_scan)

        # 禁用UI
        self.btn_scan.setEnabled(False)
        self.btn_scan.setText("扫描中...")
        self.btn_create.setEnabled(False)
        self.tree.clear()
        self.program_count_label.setText("扫描中...")

        # 创建工作线程
        self.scan_thread = QThread()
        self.scan_worker = ScanWorker(scan_path=path_to_scan, blocklist=self.blocklist)
        self.scan_worker.moveToThread(self.scan_thread)

        # 连接信号
        self.scan_worker.log.connect(self.log)
        self.scan_worker.finished.connect(self.on_scan_finished)
        self.scan_thread.started.connect(self.scan_worker.run)
        self.scan_worker.finished.connect(self.scan_thread.quit)
        self.scan_worker.finished.connect(self.scan_worker.deleteLater)
        self.scan_thread.finished.connect(self.scan_thread.deleteLater)

        # 启动线程
        self.scan_thread.start()

    # 【新】v8.4 扫描完成的槽
    @Slot(list)
    def on_scan_finished(self, programs_list):
        self.log("--- 扫描线程已完成 ---")
        self.programs = programs_list
        self.populate_main_treeview()

        # 恢复UI
        self.btn_scan.setEnabled(True)
        self.btn_scan.setText("选择目录...")
        self.btn_create.setEnabled(len(self.programs) > 0)
        self.scan_thread = None  # 清理线程
        self.scan_worker = None

    def populate_main_treeview(self):
        self.tree.clear()
        items = []
        for i, prog_data in enumerate(self.programs):
            status_text = self.get_program_status_text(prog_data)
            item = QTreeWidgetItem([prog_data['name'], status_text, prog_data['root_path']])
            item.setData(0, Qt.ItemDataRole.UserRole, i)
            items.append(item)
        self.tree.addTopLevelItems(items)
        self.tree.header().resizeSections(QHeaderView.ResizeMode.ResizeToContents)
        self.tree.header().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        # 【新】v8.4 Req 1: 更新计数
        self.program_count_label.setText(f"总共: {len(self.programs)} 个")

    def get_program_status_text(self, prog_data):
        count = len(prog_data['selected_exes'])
        if count == 0:
            return "(未选择)"
        elif count == 1:
            return os.path.basename(prog_data['selected_exes'][0])
        else:
            return f"({count} 个文件已选)"

    def on_program_select(self):
        self.btn_refine.setEnabled(len(self.tree.selectedItems()) > 0)

    def open_refine_window(self):
        selected_items = self.tree.selectedItems()
        if not selected_items: return

        program_index = selected_items[0].data(0, Qt.ItemDataRole.UserRole)
        program_data = self.programs[program_index]
        self.log(f"--- 打开详情: {program_data['name']} ---")

        refine_win = RefineWindow(self, program_data)
        if refine_win.exec() == QDialog.DialogCode.Accepted:
            self.log("--- 详情已确认修改 ---")
            status_text = self.get_program_status_text(program_data)
            selected_items[0].setText(1, status_text)
        else:
            self.log("--- 详情已取消 ---")

    # 【新】v8.4 Req 3: 使用自定义路径
    def generate_shortcuts(self):
        # 1. 获取自定义输出路径
        output_dir = self.output_path_edit.text().strip()

        # 2. 如果为空，使用默认路径
        if not output_dir:
            desktop_path = os.path.join(os.path.expanduser('~'), 'Desktop')
            output_dir = os.path.join(desktop_path, backend.DEFAULT_OUTPUT_FOLDER_NAME)
            self.log(f"未指定输出目录，使用默认: {output_dir}")

        if not os.path.exists(output_dir):
            try:
                os.makedirs(output_dir); self.log(f"已创建输出文件夹: {output_dir}")
            except Exception as e:
                self.log(f"[!] 无法创建目录: {e}");
                QMessageBox.critical(self, "错误", f"无法创建输出文件夹: {output_dir}");
                return

        total_created = 0;
        total_failed = 0
        self.log("--- 开始批量创建快捷方式 ---")
        for program in self.programs:
            if not program['selected_exes']: continue
            self.log(f"  正在处理程序: {program['name']}")
            for full_path in program['selected_exes']:
                # 3. 使用最终的 output_dir
                shortcut_path = os.path.join(output_dir, f"{os.path.splitext(os.path.basename(full_path))[0]}.lnk")

                success, msg = backend.create_shortcut(full_path, shortcut_path)
                self.log(f"    {msg}")  # 使用 self.log
                if success:
                    total_created += 1
                else:
                    total_failed += 1

        self.log("--- 全部处理完成 ---")
        QMessageBox.information(self, "操作完成",
                                f"操作已在桌面 '{output_dir}' 文件夹中完成。\n\n"
                                f"成功: {total_created} 个\n失败: {total_failed} 个\n\n"
                                "详细日志请查看主窗口。")

    # 【新】v8.4 保存所有新配置
    def closeEvent(self, event: QCloseEvent):
        self.log("正在保存配置...")
        self.config['Settings']['last_scan_path'] = self.path_edit.text()
        geo = self.geometry()
        self.config['Settings']['window_geometry'] = f"{geo.width()}x{geo.height()}+{geo.x()}+{geo.y()}"
        # 保存主题和输出路径
        self.config['Settings']['theme'] = 'light' if self.theme_combo.currentIndex() == 1 else 'dark'
        self.config['Settings']['output_path'] = self.output_path_edit.text()

        backend.save_config(self.config)
        event.accept()


# --- 启动主程序 ---
if __name__ == "__main__":
    if os.name != 'nt':
        print("错误：此脚本需要 Windows (pywin32) 和 PySide6 环境。")
    else:
        # 为高DPI屏幕启用缩放
        if hasattr(Qt, 'AA_EnableHighDpiScaling'):
            QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
        if hasattr(Qt, 'AA_UseHighDpiPixmaps'):
            QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

        app = QApplication(sys.argv)

        # 样式表在 MainWindow 中加载，以便能读取配置
        window = MainWindow()
        window.show()
        sys.exit(app.exec())