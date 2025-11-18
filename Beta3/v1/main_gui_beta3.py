import sys
import os
import re

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QFrame, QFileDialog, QLineEdit, QLabel, QTreeWidget,
    QTreeWidgetItem, QHeaderView, QDialog, QDialogButtonBox,
    QMessageBox, QTextEdit, QStackedWidget, QButtonGroup, QComboBox,
    QFileIconProvider, QStyle, QStatusBar, QProgressBar
)
from PySide6.QtCore import Qt, QSize, QObject, Signal, Slot, QThread, QFileInfo
from PySide6.QtGui import QCloseEvent, QIcon

# 导入后端
import scanner_backend as backend

# --- Beta 3.0 样式表 (新增了 Stop 按钮样式) ---

COMMON_CSS = """
/* 红色停止按钮 */
QPushButton[objectName="stopButton"] {
    background-color: #D94430; color: #FFFFFF; border: 1px solid #B03020; font-weight: bold;
}
QPushButton[objectName="stopButton"]:hover { background-color: #E05545; }
QPushButton[objectName="stopButton"]:pressed { background-color: #C02010; }
"""

LIGHT_STYLESHEET = COMMON_CSS + """
QWidget { font-family: "Microsoft YaHei UI", "Segoe UI", sans-serif; font-size: 10pt; color: #000000; }
QMainWindow { background-color: #F0F0F0; }
QWidget[objectName="sidebar"] { background-color: #E0E0E0; border-right: 1px solid #C0C0C0; }
QWidget[objectName="mainArea"] { background-color: #F0F0F0; }

QPushButton[objectName="navButton"] {
    background-color: transparent; color: #333333; border: none; padding: 10px; text-align: left; border-radius: 4px; margin: 2px 10px;
}
QPushButton[objectName="navButton"]:checked { background-color: #0078D7; color: #FFFFFF; font-weight: bold; }
QPushButton[objectName="navButton"]:hover { background-color: #D0D0D0; }

QPushButton { background-color: #FFFFFF; border: 1px solid #CCCCCC; border-radius: 4px; padding: 6px 12px; }
QPushButton:hover { background-color: #F5F5F5; }

QPushButton[objectName="primaryButton"] { background-color: #0078D7; color: #FFFFFF; border: none; font-weight: bold; }
QPushButton[objectName="primaryButton"]:hover { background-color: #006CC1; }
QPushButton[objectName="primaryButton"]:disabled { background-color: #A0A0A0; }

QLineEdit, QTextEdit, QComboBox, QTreeWidget { background-color: #FFFFFF; border: 1px solid #CCCCCC; border-radius: 4px; padding: 4px; }
QTreeWidget::item { padding: 6px; }
QTreeWidget::item:selected { background-color: #0078D7; color: #FFFFFF; }
QHeaderView::section { background-color: #E5E5E5; border: none; padding: 6px; font-weight: bold; border-right: 1px solid #D0D0D0; }
"""

DARK_STYLESHEET = COMMON_CSS + """
QWidget { font-family: "Microsoft YaHei UI", "Segoe UI", sans-serif; font-size: 10pt; color: #F0F0F0; }
QMainWindow { background-color: #2B2B2B; }
QWidget[objectName="sidebar"] { background-color: #202020; border-right: 1px solid #333333; }
QWidget[objectName="mainArea"] { background-color: #2B2B2B; }

QPushButton[objectName="navButton"] {
    background-color: transparent; color: #CCCCCC; border: none; padding: 10px; text-align: left; border-radius: 4px; margin: 2px 10px;
}
QPushButton[objectName="navButton"]:checked { background-color: #0078D7; color: #FFFFFF; font-weight: bold; }
QPushButton[objectName="navButton"]:hover { background-color: #333333; }

QPushButton { background-color: #3A3A3A; border: 1px solid #555555; border-radius: 4px; padding: 6px 12px; color: #F0F0F0; }
QPushButton:hover { background-color: #454545; }

QPushButton[objectName="primaryButton"] { background-color: #0078D7; color: #FFFFFF; border: none; font-weight: bold; }
QPushButton[objectName="primaryButton"]:hover { background-color: #006CC1; }
QPushButton[objectName="primaryButton"]:disabled { background-color: #444444; color: #888888; }

QLineEdit, QTextEdit, QComboBox, QTreeWidget { background-color: #252525; border: 1px solid #444444; border-radius: 4px; padding: 4px; color: #F0F0F0; }
QTreeWidget::item { padding: 6px; }
QTreeWidget::item:selected { background-color: #0078D7; color: #FFFFFF; }
QHeaderView::section { background-color: #333333; border: none; padding: 6px; font-weight: bold; border-right: 1px solid #444444; }
"""


# --- 扫描工作线程 (Beta 3.0: 支持停止) ---
class ScanWorker(QObject):
    finished = Signal(list)
    log = Signal(str)

    def __init__(self, scan_path, blocklist):
        super().__init__()
        self.scan_path = scan_path
        self.blocklist = blocklist
        self.is_running = True  # 运行标志位

    @Slot()
    def stop(self):
        """接收停止信号"""
        self.is_running = False

    @Slot()
    def run(self):
        try:
            # 回调函数：检查是否应停止
            def check_stop():
                return not self.is_running

            # 传递 log 信号和 check_stop 回调
            programs = backend.discover_programs(
                self.scan_path,
                self.blocklist,
                self.log.emit,
                check_stop_callback=check_stop
            )
            self.finished.emit(programs)
        except Exception as e:
            self.log.emit(f"!!! 错误: {str(e)}")
            self.finished.emit([])


# --- 详情弹窗 (Stage 2) ---
class RefineWindow(QDialog):
    def __init__(self, parent, program_data):
        super().__init__(parent)
        self.setWindowTitle(f"修改程序详情: {program_data['name']}")  # 优化标题
        self.setMinimumSize(700, 500)
        self.setModal(True)
        self.program_data = program_data
        self.all_exes = program_data['all_exes']
        self.original_selection = set(program_data['selected_exes'])
        self.icon_provider = QFileIconProvider()  # 用于获取图标

        self.build_ui()
        self.populate_tree()
        self.pre_select_items()
        self.on_filter_changed()

    def build_ui(self):
        layout = QVBoxLayout(self)

        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("筛选:"))
        self.filter_edit = QLineEdit()
        self.filter_edit.setPlaceholderText("输入名称进行筛选...")
        self.filter_edit.textChanged.connect(self.on_filter_changed)
        filter_layout.addWidget(self.filter_edit)
        layout.addLayout(filter_layout)

        self.tree = QTreeWidget()
        self.tree.setColumnCount(3)
        self.tree.setHeaderLabels(['程序名', '大小', '路径'])
        self.tree.setSelectionMode(QTreeWidget.SelectionMode.ExtendedSelection)
        self.tree.setSortingEnabled(True)
        self.tree.header().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.tree.header().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
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
            # 获取图标
            icon = self.icon_provider.icon(QFileInfo(full_path))
            item.setIcon(0, icon)

            item.setData(0, Qt.ItemDataRole.UserRole, full_path)
            item.setData(1, Qt.ItemDataRole.UserRole, size_bytes)
            item.setData(1, Qt.ItemDataRole.DisplayRole, size_bytes)
            items.append(item)
        self.tree.addTopLevelItems(items)
        for item in items:
            size_mb = f"{item.data(1, Qt.ItemDataRole.UserRole) / (1024 * 1024):.2f} MB"
            item.setText(1, size_mb)
        self.tree.setSortingEnabled(True)

    # ... (pre_select_items, on_filter_changed 等辅助函数保持不变) ...
    def pre_select_items(self):
        for item in self.tree.findItems("", Qt.MatchFlag.MatchContains | Qt.MatchFlag.MatchRecursive, 0):
            if item.data(0, Qt.ItemDataRole.UserRole) in self.original_selection:
                item.setSelected(True)

    def on_filter_changed(self, text=""):
        query = self.filter_edit.text().lower()
        for i in range(self.tree.topLevelItemCount()):
            item = self.tree.topLevelItem(i)
            hidden = not (query in item.text(0).lower() or query in item.text(2).lower())
            item.setHidden(hidden)

    def select_all_visible(self):
        for i in range(self.tree.topLevelItemCount()):
            if not self.tree.topLevelItem(i).isHidden(): self.tree.topLevelItem(i).setSelected(True)

    def select_none(self):
        self.tree.clearSelection()

    def on_ok(self):
        self.program_data['selected_exes'] = tuple(
            [item.data(0, Qt.ItemDataRole.UserRole) for item in self.tree.selectedItems()])
        self.accept()


# --- 主窗口 (Beta 3.0) ---
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("快捷方式扫描器 (Beta 3.0)")
        self.config = backend.load_config()
        self.programs = []
        self.blocklist, msg_blocklist = backend.load_blocklist()

        # 线程相关
        self.scan_thread = None
        self.scan_worker = None
        self.icon_provider = QFileIconProvider()  # 用于主列表图标

        self.build_ui()
        self.setup_status_bar()

        # 初始化
        self.log_to_settings(f"程序已启动。{msg_blocklist}")
        self.load_geometry_theme()
        self.output_path_edit.setText(self.config.get('Settings', 'output_path', fallback=''))

        # 加载上次路径
        last_path = self.config.get('Settings', 'last_scan_path', fallback='')
        if last_path:
            self.path_edit.setText(last_path)
            # 【新】如果已有路径，直接启用“开始扫描”按钮
            self.btn_start_stop.setEnabled(True)

    def load_geometry_theme(self):
        geo_str = self.config.get('Settings', 'window_geometry', fallback='')
        if geo_str:
            try:
                w, h, x, y = map(int, re.split(r'[x+]', geo_str))
                self.resize(QSize(w, h));
                self.move(x, y)
            except:
                self.resize(900, 700)

        theme = self.config.get('Settings', 'theme', fallback='dark')
        self.theme_combo.setCurrentIndex(1 if theme == 'light' else 0)

    def setup_status_bar(self):
        # 【新】状态栏，替代首页日志
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_label = QLabel("准备就绪")
        self.status_label.setStyleSheet("color: #888888;")
        self.status_bar.addWidget(self.status_label)

        # 进度条 (隐藏状态)
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximumWidth(200)
        self.progress_bar.setVisible(False)
        self.progress_bar.setRange(0, 0)  # 忙碌模式
        self.status_bar.addPermanentWidget(self.progress_bar)

    def build_ui(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        root_layout = QHBoxLayout(main_widget)
        root_layout.setContentsMargins(0, 0, 0, 0);
        root_layout.setSpacing(0)

        # --- Sidebar ---
        sidebar = QWidget();
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(200)
        sb_layout = QVBoxLayout(sidebar);
        sb_layout.setContentsMargins(0, 20, 0, 20);
        sb_layout.setSpacing(5)

        self.nav_group = QButtonGroup(self);
        self.nav_group.setExclusive(True)

        def add_nav_btn(text, id):
            btn = QPushButton(text);
            btn.setObjectName("navButton");
            btn.setCheckable(True)
            self.nav_group.addButton(btn, id);
            sb_layout.addWidget(btn)
            return btn

        sb_layout.addWidget(QLabel("  导航菜单"))
        self.nav_scan = add_nav_btn("🔍 程序扫描", 0)
        self.nav_set = add_nav_btn("⚙️ 应用设置", 1)
        sb_layout.addStretch()
        root_layout.addWidget(sidebar)

        # --- Content Area ---
        self.stack = QStackedWidget();
        self.stack.setObjectName("mainArea")
        self.stack.addWidget(self.create_scanner_view())
        self.stack.addWidget(self.create_settings_view())
        root_layout.addWidget(self.stack)

        self.nav_group.idClicked.connect(self.stack.setCurrentIndex)
        self.nav_scan.setChecked(True)

    def create_separator(self):
        f = QFrame();
        f.setFrameShape(QFrame.Shape.HLine);
        f.setFrameShadow(QFrame.Shadow.Sunken)
        return f

    # --- Page 1: Scanner ---
    def create_scanner_view(self):
        page = QWidget();
        layout = QVBoxLayout(page)
        layout.setContentsMargins(20, 20, 20, 20);
        layout.setSpacing(15)

        # 1. 路径选择区
        layout.addWidget(QLabel("第一步: 选择要扫描的文件夹 (如 D:\\Games)"))
        path_box = QHBoxLayout()
        self.path_edit = QLineEdit();
        self.path_edit.setReadOnly(True);
        self.path_edit.setPlaceholderText("未选择目录...")
        path_box.addWidget(self.path_edit)
        btn_browse = QPushButton("选择目录...");
        btn_browse.clicked.connect(self.browse_path)
        path_box.addWidget(btn_browse)
        layout.addLayout(path_box)

        # 2. 开始/停止 按钮 (Beta 3 核心功能)
        self.btn_start_stop = QPushButton("开始扫描")
        self.btn_start_stop.setObjectName("primaryButton")  # 默认样式
        self.btn_start_stop.setMinimumHeight(40)
        self.btn_start_stop.setEnabled(False)  # 没路径时禁用
        self.btn_start_stop.clicked.connect(self.toggle_scan)
        layout.addWidget(self.btn_start_stop)

        layout.addWidget(self.create_separator())

        # 3. 列表区
        head_box = QHBoxLayout()
        head_box.addWidget(QLabel("发现的程序列表 (双击可修改详情)"))
        head_box.addStretch()
        self.lbl_count = QLabel("")
        head_box.addWidget(self.lbl_count)
        layout.addLayout(head_box)

        self.tree = QTreeWidget()
        self.tree.setColumnCount(3)
        self.tree.setHeaderLabels(['程序名', '主程序 (建议)', '路径'])
        self.tree.header().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.tree.header().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.tree.setSelectionMode(QTreeWidget.SelectionMode.SingleSelection)
        # 【Beta 3】双击打开详情
        self.tree.itemDoubleClicked.connect(self.open_refine_window)
        layout.addWidget(self.tree)

        layout.addWidget(self.create_separator())

        # 4. 底部操作
        action_box = QHBoxLayout()
        action_box.addStretch()
        self.btn_gen = QPushButton("生成所有快捷方式")
        self.btn_gen.setObjectName("primaryButton")
        self.btn_gen.setMinimumHeight(40);
        self.btn_gen.setMinimumWidth(200)
        self.btn_gen.setEnabled(False)
        self.btn_gen.clicked.connect(self.generate_shortcuts)
        action_box.addWidget(self.btn_gen)
        layout.addLayout(action_box)

        return page

    # --- Page 2: Settings ---
    def create_settings_view(self):
        page = QWidget();
        layout = QVBoxLayout(page)
        layout.setContentsMargins(20, 20, 20, 20);
        layout.setSpacing(15)

        layout.addWidget(QLabel("外观设置"), 0, Qt.AlignmentFlag.AlignBottom)
        theme_box = QHBoxLayout()
        theme_box.addWidget(QLabel("界面主题:"))
        self.theme_combo = QComboBox();
        self.theme_combo.addItems(["暗黑模式 (Dark)", "明亮模式 (Light)"])
        self.theme_combo.currentIndexChanged.connect(self.change_theme)
        theme_box.addWidget(self.theme_combo);
        theme_box.addStretch()
        layout.addLayout(theme_box)

        layout.addWidget(self.create_separator())

        layout.addWidget(QLabel("生成设置"), 0, Qt.AlignmentFlag.AlignBottom)
        out_box = QHBoxLayout()
        self.output_path_edit = QLineEdit();
        self.output_path_edit.setPlaceholderText("留空则默认生成到桌面的 'MyTestShortcuts' 文件夹")
        out_box.addWidget(QLabel("输出目录:"));
        out_box.addWidget(self.output_path_edit)
        btn_out = QPushButton("浏览...");
        btn_out.clicked.connect(self.browse_output)
        out_box.addWidget(btn_out)
        layout.addLayout(out_box)

        layout.addWidget(self.create_separator())

        layout.addWidget(QLabel("黑名单设置 (blocklist.txt)"), 0, Qt.AlignmentFlag.AlignBottom)
        self.blocklist_edit = QTextEdit();
        self.blocklist_edit.setPlainText("\n".join(sorted(self.blocklist)))
        self.blocklist_edit.setMaximumHeight(150)
        layout.addWidget(self.blocklist_edit)
        btn_save_blk = QPushButton("保存黑名单");
        btn_save_blk.clicked.connect(self.save_blocklist)
        layout.addWidget(btn_save_blk, 0, Qt.AlignmentFlag.AlignRight)

        layout.addWidget(self.create_separator())

        # 【Beta 3】完整日志移到这里
        layout.addWidget(QLabel("运行日志"), 0, Qt.AlignmentFlag.AlignBottom)
        self.log_edit = QTextEdit();
        self.log_edit.setReadOnly(True);
        self.log_edit.setObjectName("logArea")
        layout.addWidget(self.log_edit)

        return page

    # --- Logic ---

    def browse_path(self):
        d = QFileDialog.getExistingDirectory(self, "选择扫描目录", self.path_edit.text() or ".")
        if d:
            self.path_edit.setText(d)
            self.btn_start_stop.setEnabled(True)  # 有路径了，可以开始
            self.btn_start_stop.setText("开始扫描")

    def browse_output(self):
        d = QFileDialog.getExistingDirectory(self, "选择输出目录", self.output_path_edit.text() or ".")
        if d: self.output_path_edit.setText(d)

    # 【Beta 3 核心】开始/停止 切换逻辑
    def toggle_scan(self):
        # 情况 A: 正在扫描 -> 请求停止
        if self.scan_thread and self.scan_thread.isRunning():
            self.btn_start_stop.setEnabled(False)  # 防连击
            self.btn_start_stop.setText("正在停止...")
            self.status_label.setText("正在停止扫描...")
            # 向 Worker 发送停止信号 (通过方法调用)
            if self.scan_worker:
                self.scan_worker.stop()
            return

        # 情况 B: 未扫描 -> 开始扫描
        scan_path = self.path_edit.text()
        if not scan_path: return

        # UI 状态更新
        self.btn_start_stop.setText("停止扫描")
        self.btn_start_stop.setObjectName("stopButton")  # 变红
        self.btn_start_stop.setStyle(self.btn_start_stop.style())  # 强制刷新样式
        self.btn_gen.setEnabled(False)
        self.tree.clear()
        self.status_label.setText(f"正在扫描: {scan_path}")
        self.progress_bar.setVisible(True)
        self.log_to_settings(f"--- 开始扫描: {scan_path} ---")

        # 启动线程
        self.scan_thread = QThread(self)
        self.scan_worker = ScanWorker(scan_path, self.blocklist)
        self.scan_worker.moveToThread(self.scan_thread)

        self.scan_worker.log.connect(self.handle_worker_log)  # 简单日志 -> 状态栏/设置
        self.scan_worker.finished.connect(self.on_scan_finished)
        self.scan_thread.started.connect(self.scan_worker.run)
        self.scan_worker.finished.connect(self.scan_thread.quit)
        self.scan_thread.finished.connect(self.scan_worker.deleteLater)
        self.scan_thread.finished.connect(self.scan_thread.deleteLater)
        self.scan_thread.finished.connect(self.cleanup_thread)

        self.scan_thread.start()

    @Slot(str)
    def handle_worker_log(self, msg):
        # 实时日志：简略信息显示在状态栏，完整信息记录到设置页
        self.log_to_settings(msg)
        # 状态栏只显示简短状态，避免刷屏太快
        if msg.startswith("[!]"):
            self.status_label.setText(msg)
        elif "发现" in msg:
            self.status_label.setText(msg)

    @Slot(list)
    def on_scan_finished(self, programs):
        self.programs = programs
        self.populate_tree()

        # 恢复 UI 状态
        self.progress_bar.setVisible(False)
        self.btn_start_stop.setEnabled(True)
        self.btn_start_stop.setText("开始扫描")
        self.btn_start_stop.setObjectName("primaryButton")  # 恢复蓝色 (需重置 objectName)
        # 注意：这里我们需要稍微 hack 一下，因为 primaryButton 样式可能需要重置
        self.btn_start_stop.setObjectName("")
        self.btn_start_stop.setStyle(self.btn_start_stop.style())

        self.btn_gen.setEnabled(len(programs) > 0)
        self.status_label.setText(f"扫描完成。共找到 {len(programs)} 个程序。")
        self.lbl_count.setText(f"共 {len(programs)} 个")
        self.log_to_settings("--- 扫描结束 ---")

    @Slot()
    def cleanup_thread(self):
        self.scan_thread = None;
        self.scan_worker = None

    def populate_tree(self):
        self.tree.clear()
        items = []
        # 【Beta 3】这里是在主线程，可以安全创建图标
        # 如果程序很多 (>500)，这里可能会卡顿 0.5s 左右，这是可接受的
        for i, p in enumerate(self.programs):
            # 提取主程序的图标
            exe_path = p['selected_exes'][0] if p['selected_exes'] else ""
            icon = QIcon()
            if exe_path and os.path.exists(exe_path):
                icon = self.icon_provider.icon(QFileInfo(exe_path))

            display_name = p['name']
            selected_name = os.path.basename(exe_path) if exe_path else "(无)"

            item = QTreeWidgetItem([display_name, selected_name, p['root_path']])
            item.setIcon(0, icon)  # 设置图标
            item.setData(0, Qt.ItemDataRole.UserRole, i)
            items.append(item)
        self.tree.addTopLevelItems(items)

    def open_refine_window(self, item=None):
        # 支持双击 (传递 item) 或 按钮点击 (无 item，取当前选中)
        if item is None:
            items = self.tree.selectedItems()
            if not items: return
            item = items[0]

        idx = item.data(0, Qt.ItemDataRole.UserRole)
        prog = self.programs[idx]

        win = RefineWindow(self, prog)
        if win.exec() == QDialog.DialogCode.Accepted:
            # 更新列表显示
            new_exe = prog['selected_exes'][0] if prog['selected_exes'] else "(无)"
            item.setText(1, os.path.basename(new_exe))
            # 更新图标
            if prog['selected_exes']:
                item.setIcon(0, self.icon_provider.icon(QFileInfo(prog['selected_exes'][0])))

    def log_to_settings(self, msg):
        self.log_edit.append(msg)

    def change_theme(self, idx):
        is_light = (idx == 1)
        self.config['Settings']['theme'] = 'light' if is_light else 'dark'
        QApplication.instance().setStyleSheet(LIGHT_STYLESHEET if is_light else DARK_STYLESHEET)

    def save_blocklist(self):
        txt = self.blocklist_edit.toPlainText()
        new_set = {line.strip().lower() for line in txt.split('\n') if line.strip()}
        ok, msg = backend.save_blocklist(new_set)
        if ok:
            QMessageBox.information(self, "成功", msg); self.blocklist = new_set
        else:
            QMessageBox.warning(self, "失败", msg)

    def generate_shortcuts(self):
        out_dir = self.output_path_edit.text().strip()
        if not out_dir:
            desktop = os.path.join(os.path.expanduser('~'), 'Desktop')
            out_dir = os.path.join(desktop, backend.DEFAULT_OUTPUT_FOLDER_NAME)

        if not os.path.exists(out_dir):
            try:
                os.makedirs(out_dir)
            except:
                QMessageBox.critical(self, "错误", f"无法创建目录: {out_dir}"); return

        count = 0
        for p in self.programs:
            for exe in p['selected_exes']:
                lnk = os.path.join(out_dir, f"{os.path.splitext(os.path.basename(exe))[0]}.lnk")
                ok, _ = backend.create_shortcut(exe, lnk)
                if ok: count += 1

        QMessageBox.information(self, "完成", f"已在 '{out_dir}' 生成 {count} 个快捷方式。")

    def closeEvent(self, e):
        # 保存配置
        self.config['Settings']['last_scan_path'] = self.path_edit.text()
        self.config['Settings']['output_path'] = self.output_path_edit.text()
        geo = self.geometry()
        self.config['Settings']['window_geometry'] = f"{geo.width()}x{geo.height()}+{geo.x()}+{geo.y()}"
        backend.save_config(self.config)
        # 停止线程
        if self.scan_worker: self.scan_worker.stop()
        e.accept()


if __name__ == "__main__":
    if hasattr(Qt, 'AA_EnableHighDpiScaling'): QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    if hasattr(Qt, 'AA_UseHighDpiPixmaps'): QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)
    # 初始加载暗黑主题 (后续由 MainWindow 读取配置覆盖)
    app.setStyleSheet(DARK_STYLESHEET)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())