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

# --- 【新】Stage 2 (详情) 弹窗 ---
class RefineWindow(QDialog):
    """
    "Stage 2" 弹窗: 单个程序的 .exe 精细选择器 (PySide6版)
    """
    def __init__(self, parent, program_data):
        super().__init__(parent)
        self.setWindowTitle(f"详情: {program_data['name']}")
        self.setMinimumSize(700, 500)
        self.setModal(True) # 设为模态对话框

        self.program_data = program_data
        # all_exes 格式: [(full_path, file_name, size_bytes, relative_path), ...]
        self.all_exes = program_data['all_exes']
        self.original_selection = set(program_data['selected_exes'])
        
        self.build_ui()
        self.populate_tree()
        self.pre_select_items()
        self.on_filter_changed() # 初始填充一次

    def build_ui(self):
        layout = QVBoxLayout(self)

        # --- 筛选 ---
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("筛选:"))
        self.filter_edit = QLineEdit()
        self.filter_edit.setPlaceholderText("按名称或路径筛选...")
        self.filter_edit.textChanged.connect(self.on_filter_changed)
        filter_layout.addWidget(self.filter_edit)
        layout.addLayout(filter_layout)

        # --- 列表 (QTreeWidget) ---
        self.tree = QTreeWidget()
        self.tree.setColumnCount(3)
        self.tree.setHeaderLabels(['程序名', '大小', '相对路径'])
        self.tree.setSelectionMode(QTreeWidget.SelectionMode.ExtendedSelection)
        self.tree.setSortingEnabled(True) # 【关键】原生支持排序

        # 设置列宽
        header = self.tree.header()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)

        layout.addWidget(self.tree)

        # --- 底部按钮 ---
        btn_layout = QHBoxLayout()
        
        btn_all = QPushButton("全选 (可见)")
        btn_all.clicked.connect(self.select_all_visible)
        btn_none = QPushButton("全不选")
        btn_none.clicked.connect(self.select_none)
        
        # 使用 QDialogButtonBox 来管理 "OK" 和 "Cancel"
        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.button_box.accepted.connect(self.on_ok)
        self.button_box.rejected.connect(self.reject) # reject 会自动关闭窗口

        btn_layout.addWidget(btn_all)
        btn_layout.addWidget(btn_none)
        btn_layout.addStretch()
        btn_layout.addWidget(self.button_box)
        layout.addLayout(btn_layout)
        
    def populate_tree(self):
        """填充 Treeview 列表"""
        # 关闭排序以提高填充速度
        self.tree.setSortingEnabled(False)
        
        items = []
        for (full_path, file_name, size_bytes, relative_path) in self.all_exes:
            size_mb = f"{size_bytes / (1024*1024):.2f} MB"
            
            # 【关键】QTreeWidgetItem 支持多列数据
            item = QTreeWidgetItem([file_name, size_mb, relative_path])
            
            # 存储原始数据以便排序和引用
            item.setData(0, Qt.ItemDataRole.UserRole, full_path) # 用 UserRole 存储 full_path
            item.setData(1, Qt.ItemDataRole.UserRole, size_bytes) # 用 UserRole 存储原始字节数

            # 【关键】为了让数字列能正确排序
            item.setData(1, Qt.ItemDataRole.DisplayRole, size_bytes) 
            # PySide6 的 TreeView 排序会查看 DisplayRole。
            # 我们必须给它原始数字 (size_bytes) 而不是字符串 ("1.40 MB")
            # 但我们又想显示 "MB"，所以我们在 populate 之后重置显示
            
            items.append(item)
            
        self.tree.addTopLevelItems(items)
        
        # 【关键】恢复显示 MB 并恢复排序
        for item in items:
            size_mb = f"{item.data(1, Qt.ItemDataRole.UserRole) / (1024*1024):.2f} MB"
            item.setText(1, size_mb) # 现在再把它设置为字符串
            
        self.tree.setSortingEnabled(True)

    def pre_select_items(self):
        """根据传入的 selected_exes 预先选中行"""
        for item in self.tree.findItems("", Qt.MatchFlag.MatchContains | Qt.MatchFlag.MatchRecursive, 0):
            full_path = item.data(0, Qt.ItemDataRole.UserRole)
            if full_path in self.original_selection:
                item.setSelected(True)

    def on_filter_changed(self, text=""):
        """实时筛选 Treeview"""
        query = self.filter_edit.text().lower()
        # 遍历所有顶层项
        for i in range(self.tree.topLevelItemCount()):
            item = self.tree.topLevelItem(i)
            # 检查文件名和路径是否匹配
            name_match = query in item.text(0).lower()
            path_match = query in item.text(2).lower()
            item.setHidden(not (name_match or path_match))

    def select_all_visible(self):
        """全选当前可见 (未被过滤掉) 的项"""
        self.select_none()
        for i in range(self.tree.topLevelItemCount()):
            item = self.tree.topLevelItem(i)
            if not item.isHidden():
                item.setSelected(True)
            
    def select_none(self):
        self.tree.clearSelection()

    def on_ok(self):
        """保存选择并关闭"""
        selected_paths = []
        for item in self.tree.selectedItems():
            selected_paths.append(item.data(0, Qt.ItemDataRole.UserRole))
            
        self.program_data['selected_exes'] = tuple(selected_paths)
        self.accept() # accept 会关闭窗口并返回 QDialog.DialogCode.Accepted

# --- 【新】Stage 1 (主窗口) 应用 ---
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("快捷方式扫描器 (v8.1-PySide6)")
        
        # 加载配置
        self.config = backend.load_config()
        geometry = self.config.get('Settings', 'window_geometry', fallback='800x600')
        # PySide6 需要 QSize
        try:
            w, h, x, y = map(int, re.split(r'[x+]', geometry))
            self.resize(QSize(w, h))
            self.move(x, y)
        except Exception:
            self.resize(QSize(800, 600))

        self.programs = []
        
        # 加载黑名单
        self.blocklist, msg = backend.load_blocklist()

        self.build_ui()
        
        self.log(f"程序已启动。{msg}")
        self.log("请选择一个目录进行“程序发现”。")

    def build_ui(self):
        # 中心部件
        main_widget = QWidget()
        main_layout = QVBoxLayout(main_widget)
        self.setCentralWidget(main_widget)

        # --- 顶部：扫描控制 ---
        top_layout = QHBoxLayout()
        self.btn_scan = QPushButton("1. 选择扫描目录...")
        self.btn_scan.setMinimumHeight(35) # 让按钮更高
        self.btn_scan.clicked.connect(self.ask_scan_path)
        top_layout.addWidget(self.btn_scan)
        
        self.btn_blocklist = QPushButton("管理黑名单")
        self.btn_blocklist.setMinimumHeight(35)
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

        # --- 底部：执行按钮 ---
        self.btn_create = QPushButton("3. 生成所有快捷方式")
        self.btn_create.setEnabled(False)
        self.btn_create.setMinimumHeight(35)
        self.btn_create.clicked.connect(self.generate_shortcuts)
        main_layout.addWidget(self.btn_create)

        # --- 日志区 ---
        main_layout.addWidget(QLabel("--- 日志输出 ---"))
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        self.log_area.setMaximumHeight(150) # 限制日志区高度
        main_layout.addWidget(self.log_area)

    def log(self, message):
        """(UI功能) 向日志区域追加一条消息"""
        self.log_area.append(message) # append 会自动换行
        self.log_area.verticalScrollBar().setValue(self.log_area.verticalScrollBar().maximum())
        QApplication.processEvents() # 强制 UI 刷新

    def show_blocklist(self):
        """(UI功能) 管理黑名单的弹窗"""
        # PySide6 没有 Toplevel，我们用 QDialog
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
                popup.accept() # 关闭弹窗
            else:
                QMessageBox.critical(popup, "保存失败", msg)
        
        button_box.accepted.connect(on_save)
        button_box.rejected.connect(popup.reject)
        layout.addWidget(button_box)
        
        popup.exec() # 以模态方式显示

    def ask_scan_path(self):
        """(UI功能) 扫描按钮点击事件"""
        initial_dir = self.config.get('Settings', 'last_scan_path', fallback=None)
        
        path_to_scan = QFileDialog.getExistingDirectory(self, "选择扫描目录", initial_dir)
        
        if not path_to_scan:
            self.log("[提示] 用户取消了目录选择。")
            return 
            
        self.path_edit.setText(path_to_scan)
        
        # 【关键】调用后端扫描，并把 UI 的 log 方法传进去
        self.programs = backend.discover_programs(path_to_scan, self.blocklist, self.log)
        
        self.populate_main_treeview()
        self.btn_create.setEnabled(len(self.programs) > 0)

    def populate_main_treeview(self):
        """(UI功能) 填充主列表"""
        self.tree.clear()
        
        items = []
        for i, prog_data in enumerate(self.programs):
            status_text = self.get_program_status_text(prog_data)
            
            item = QTreeWidgetItem([prog_data['name'], status_text, prog_data['root_path']])
            # 存储索引，以便稍后引用 self.programs 列表
            item.setData(0, Qt.ItemDataRole.UserRole, i) 
            items.append(item)
            
        self.tree.addTopLevelItems(items)
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
        """当用户在主列表选择一行时"""
        self.btn_refine.setEnabled(len(self.tree.selectedItems()) > 0)

    def open_refine_window(self):
        """打开 Stage 2 详情弹窗"""
        selected_items = self.tree.selectedItems()
        if not selected_items:
            return
        
        # 从 QTreeItem 中取回我们存储的索引
        program_index = selected_items[0].data(0, Qt.ItemDataRole.UserRole)
        program_data = self.programs[program_index]
        
        self.log(f"--- 打开详情: {program_data['name']} ---")
        
        # 启动弹窗
        refine_win = RefineWindow(self, program_data)
        
        # exec() 会阻塞，直到弹窗关闭
        if refine_win.exec() == QDialog.DialogCode.Accepted:
            # 只有点击 "OK" 才刷新
            self.log("--- 详情已确认修改 ---")
            status_text = self.get_program_status_text(program_data)
            selected_items[0].setText(1, status_text)
        else:
            self.log("--- 详情已取消 ---")

    def generate_shortcuts(self):
        """(UI功能) 生成按钮点击事件"""
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
                # 【关键】调用后端创建
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
        """(UI功能) 捕获窗口关闭事件"""
        self.log("正在保存配置...")
        self.config['Settings']['last_scan_path'] = self.path_edit.text()
        # PySide6 保存几何信息
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
        window = MainWindow()
        window.show()
        sys.exit(app.exec())