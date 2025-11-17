import sys
import os
import re

# 导入 PySide6
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QPushButton, QFrame, QFileDialog, QLineEdit, QLabel, QTreeWidget, 
    QTreeWidgetItem, QHeaderView, QDialog, QDialogButtonBox, 
    QMessageBox, QTextEdit
)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QCloseEvent

# 导入我们强大的后端
import scanner_backend as backend

# --- 【新】v8.2 QSS 样式表 ---
MODERN_STYLESHEET = """
/* 全局样式 */
QWidget {
    background-color: #2B2B2B; /* 深灰背景 */
    color: #F0F0F0; /* 亮灰文字 */
    font-family: "Microsoft YaHei UI", "Segoe UI", Arial, sans-serif;
    font-size: 10pt;
}

/* 主窗口 */
QMainWindow {
    background-color: #2B2B2B;
}

/* 标签 */
QLabel {
    background-color: transparent;
    color: #AAAAAA; /* 标签文字使用稍暗的灰色 */
    font-size: 9pt;
}

/* 按钮 */
QPushButton {
    background-color: #4A4A4A; /* 按钮背景 */
    color: #F0F0F0;
    border: 1px solid #5A5A5A;
    padding: 8px 16px; /* 增加内边距，使按钮更“胖” */
    border-radius: 4px; /* 圆角 */
    min-height: 20px;
}
QPushButton:hover {
    background-color: #5A5A5A; /* 鼠标悬停 */
    border: 1px solid #6A6A6A;
}
QPushButton:pressed {
    background-color: #6A6A6A; /* 鼠标按下 */
}
QPushButton:disabled {
    background-color: #3A3A3A; /* 禁用状态 */
    color: #777777;
    border-color: #4A4A4A;
}

/* 输入框 */
QLineEdit, QTextEdit {
    background-color: #252525; /* 稍亮的背景 */
    color: #F0F0F0;
    border: 1px solid #5A5A5A;
    border-radius: 4px;
    padding: 5px;
}
QLineEdit:read-only {
    background-color: #333333;
}
QTextEdit:read-only {
    background-color: #252525;
}

/* 树形列表 (TreeWidget) */
QTreeWidget {
    background-color: #252525;
    border: 1px solid #5A5A5A;
    border-radius: 4px;
    alternate-background-color: #2E2E2E; /* 隔行变色 */
}
QTreeWidget::item {
    padding: 5px;
}
QTreeWidget::item:selected {
    background-color: #0078D7; /* 选中项的背景色 (蓝色) */
    color: #FFFFFF;
}
QTreeWidget::item:hover {
    background-color: #3A3A3A;
}

/* 列表头部 */
QHeaderView::section {
    background-color: #3A3A3A;
    color: #F0F0F0;
    padding: 5px;
    border: 1px solid #5A5A5A;
    font-weight: bold;
}

/* 对话框 (详情/黑名单) */
QDialog {
    background-color: #2B2B2B;
}

/* 滚动条 */
QScrollBar:vertical {
    border: 1px solid #3A3A3A;
    background: #2B2B2B;
    width: 15px;
    margin: 15px 0 15px 0;
}
QScrollBar::handle:vertical {
    background: #4A4A4A;
    min-height: 20px;
    border-radius: 7px;
}
QScrollBar::handle:vertical:hover {
    background: #5A5A5A;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 15px;
    subcontrol-origin: margin;
}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
    background: none;
}

QScrollBar:horizontal {
    border: 1px solid #3A3A3A;
    background: #2B2B2B;
    height: 15px;
    margin: 0 15px 0 15px;
}
QScrollBar::handle:horizontal {
    background: #4A4A4A;
    min-width: 20px;
    border-radius: 7px;
}
QScrollBar::handle:horizontal:hover {
    background: #5A5A5A;
}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 15px;
    subcontrol-origin: margin;
}
QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {
    background: none;
}

/* 分隔线 */
QFrame[frameShape="4"] { /* 4 = HLine */
    color: #4A4A4A;
}
"""


# --- Stage 2 (详情) 弹窗 (与 v8.1 完全相同) ---
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
            item = QTreeWidgetItem([file_name, "", relative_path]) # 暂时不设置大小
            item.setData(0, Qt.ItemDataRole.UserRole, full_path) 
            item.setData(1, Qt.ItemDataRole.UserRole, size_bytes) 
            item.setData(1, Qt.ItemDataRole.DisplayRole, size_bytes) 
            items.append(item)
            
        self.tree.addTopLevelItems(items)
        
        for item in items:
            size_mb = f"{item.data(1, Qt.ItemDataRole.UserRole) / (1024*1024):.2f} MB"
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

# --- 【新】Stage 1 (主窗口) 应用 (已美化布局) ---
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("快捷方式扫描器 (v8.2-PySide6)")
        
        self.config = backend.load_config()
        geometry = self.config.get('Settings', 'window_geometry', fallback='800x600')
        try:
            w, h, x, y = map(int, re.split(r'[x+]', geometry))
            self.resize(QSize(w, h))
            self.move(x, y)
        except Exception:
            self.resize(QSize(800, 600))

        self.programs = []
        self.blocklist, msg = backend.load_blocklist()
        self.build_ui()
        self.log(f"程序已启动。{msg}")
        self.log("请选择一个目录进行“程序发现”。")

    def build_ui(self):
        main_widget = QWidget()
        # 【新】增加外边距，让 UI 不会贴着窗口边缘
        main_layout = QVBoxLayout(main_widget)
        main_layout.setContentsMargins(10, 10, 10, 10) 
        main_layout.setSpacing(10) # 增加控件间的垂直间距
        self.setCentralWidget(main_widget)

        # --- 顶部：扫描控制 ---
        top_layout = QHBoxLayout()
        self.btn_scan = QPushButton("1. 选择扫描目录...")
        self.btn_scan.clicked.connect(self.ask_scan_path)
        top_layout.addWidget(self.btn_scan)
        
        self.btn_blocklist = QPushButton("管理黑名单")
        self.btn_blocklist.clicked.connect(self.show_blocklist)
        top_layout.addWidget(self.btn_blocklist)
        main_layout.addLayout(top_layout)

        # --- 路径显示 ---
        path_layout = QHBoxLayout()
        path_layout.addWidget(QLabel("所选路径:"))
        self.path_edit = QLineEdit()
        self.path_edit.setReadOnly(True)
        self.path_edit.setText(self.config.get('Settings', 'last_scan_path', fallback=''))
        path_layout.addWidget(self.path_edit)
        main_layout.addLayout(path_layout)

        # --- 【新】分隔线 ---
        main_layout.addWidget(self.create_separator())

        # --- Stage 1: 程序发现列表 ---
        self.tree = QTreeWidget()
        self.tree.setColumnCount(3)
        self.tree.setHeaderLabels(['发现的程序', '当前选择', '程序根目录'])
        self.tree.setSelectionMode(QTreeWidget.SelectionMode.SingleSelection)
        self.tree.setSortingEnabled(False)
        header = self.tree.header()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.tree.itemSelectionChanged.connect(self.on_program_select)
        main_layout.addWidget(self.tree)

        # --- 中间按钮 ---
        self.btn_refine = QPushButton("2. 详情/修改选择...")
        self.btn_refine.setEnabled(False)
        self.btn_refine.clicked.connect(self.open_refine_window)
        main_layout.addWidget(self.btn_refine)
        
        # --- 【新】分隔线 ---
        main_layout.addWidget(self.create_separator())

        # --- 底部：执行按钮 ---
        self.btn_create = QPushButton("3. 生成所有快捷方式")
        self.btn_create.setEnabled(False)
        self.btn_create.clicked.connect(self.generate_shortcuts)
        main_layout.addWidget(self.btn_create)

        # --- 【新】分隔线 ---
        main_layout.addWidget(self.create_separator())

        # --- 日志区 ---
        main_layout.addWidget(QLabel("--- 日志输出 ---"))
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        self.log_area.setMaximumHeight(150)
        main_layout.addWidget(self.log_area)

    def create_separator(self):
        """(UI功能) 创建一个水平分隔线"""
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine) # 水平线
        line.setFrameShadow(QFrame.Shadow.Sunken)
        return line

    def log(self, message):
        self.log_area.append(message) 
        self.log_area.verticalScrollBar().setValue(self.log_area.verticalScrollBar().maximum())
        QApplication.processEvents() 

    def show_blocklist(self):
        popup = QDialog(self)
        popup.setWindowTitle("管理黑名单")
        popup.setMinimumSize(400, 300)
        popup.setModal(True)
        layout = QVBoxLayout(popup)
        layout.addWidget(QLabel("每行一个文件名 (不区分大小写):"))
        text_area = QTextEdit()
        text_area.setPlainText("\n".join(sorted(self.blocklist)))
        layout.addWidget(text_area)
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        def on_save():
            new_list = set(text_area.toPlainText().split('\n'))
            self.blocklist = {item.lower() for item in new_list if item.strip()}
            success, msg = backend.save_blocklist(self.blocklist)
            if success:
                self.log(f"[+] 黑名单已保存。")
                popup.accept() 
            else:
                QMessageBox.critical(popup, "保存失败", msg)
        button_box.accepted.connect(on_save)
        button_box.rejected.connect(popup.reject)
        layout.addWidget(button_box)
        popup.exec() 

    def ask_scan_path(self):
        initial_dir = self.config.get('Settings', 'last_scan_path', fallback=None)
        path_to_scan = QFileDialog.getExistingDirectory(self, "选择扫描目录", initial_dir)
        if not path_to_scan:
            self.log("[提示] 用户取消了目录选择。")
            return 
        self.path_edit.setText(path_to_scan)
        self.programs = backend.discover_programs(path_to_scan, self.blocklist, self.log)
        self.populate_main_treeview()
        self.btn_create.setEnabled(len(self.programs) > 0)

    def populate_main_treeview(self):
        self.tree.clear()
        items = []
        for i, prog_data in enumerate(self.programs):
            status_text = self.get_program_status_text(prog_data)
            item = QTreeWidgetItem([prog_data['name'], status_text, prog_data['root_path']])
            item.setData(0, Qt.ItemDataRole.UserRole, i) 
            items.append(item)
        self.tree.addTopLevelItems(items)
        # 【新】调整列宽以适应内容
        self.tree.header().resizeSections(QHeaderView.ResizeMode.ResizeToContents)
        self.tree.header().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)

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
        if not selected_items:
            return
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

    def generate_shortcuts(self):
        desktop_path = os.path.join(os.path.expanduser('~'), 'Desktop')
        shortcut_dir = os.path.join(desktop_path, backend.OUTPUT_FOLDER_NAME)
        if not os.path.exists(shortcut_dir):
            try:
                os.makedirs(shortcut_dir)
                self.log(f"已创建输出文件夹: {shortcut_dir}")
            except Exception as e:
                self.log(f"[!] 无法创建目录: {e}")
                QMessageBox.critical(self, "错误", f"无法创建输出文件夹: {shortcut_dir}")
                return
        total_created = 0
        total_failed = 0
        self.log("--- 开始批量创建快捷方式 ---")
        for program in self.programs:
            if not program['selected_exes']:
                continue
            self.log(f"  正在处理程序: {program['name']}")
            for full_path in program['selected_exes']:
                success, msg = backend.create_shortcut(
                    full_path, 
                    os.path.join(shortcut_dir, f"{os.path.splitext(os.path.basename(full_path))[0]}.lnk")
                )
                self.log(f"    {msg}")
                if success:
                    total_created += 1
                else:
                    total_failed += 1
        self.log("--- 全部处理完成 ---")
        QMessageBox.information(self, "操作完成", 
                            f"操作已在桌面 '{backend.OUTPUT_FOLDER_NAME}' 文件夹中完成。\n\n"
                            f"成功: {total_created} 个\n"
                            f"失败: {total_failed} 个\n\n"
                            "详细日志请查看主窗口。")

    def closeEvent(self, event: QCloseEvent):
        self.log("正在保存配置...")
        self.config['Settings']['last_scan_path'] = self.path_edit.text()
        geo = self.geometry()
        self.config['Settings']['window_geometry'] = f"{geo.width()}x{geo.height()}+{geo.x()}+{geo.y()}"
        backend.save_config(self.config)
        event.accept()

# --- 启动主程序 ---
if __name__ == "__main__":
    if os.name != 'nt':
        print("错误：此脚本需要 Windows (pywin32) 和 PySide6 环境。")
    else:
        app = QApplication(sys.argv)
        
        # --- 【关键】应用 v8.2 样式表 ---
        app.setStyleSheet(MODERN_STYLESHEET) 
        
        window = MainWindow()
        window.show()
        sys.exit(app.exec())