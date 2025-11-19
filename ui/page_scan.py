from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLineEdit, QLabel,
    QTreeWidget, QTreeWidgetItem, QHeaderView, QDialog, QDialogButtonBox,
    QCheckBox, QFileDialog, QMessageBox, QFileIconProvider  # <--- 移到这里了
)
from PySide6.QtCore import Qt, Signal, Slot, QThread, QObject, QSize, QFileInfo
from PySide6.QtGui import QIcon  # <--- 这里只保留 QIcon
import os
import scanner_backend as backend

# --- 线程类 ---
class ScanWorker(QObject):
    finished = Signal(list); log = Signal(str)
    def __init__(self, scan_path):
        super().__init__()
        self.scan_path = scan_path; self.is_running = True
    @Slot()
    def stop(self): self.is_running = False
    @Slot()
    def run(self):
        try:
            blk, _ = backend.load_blocklist()
            ign, _ = backend.load_ignored_dirs()
            programs = backend.discover_programs(self.scan_path, blk, ign, self.log.emit, lambda: not self.is_running)
            self.finished.emit(programs)
        except Exception as e:
            self.log.emit(f"Error: {e}"); self.finished.emit([])

# --- 详情弹窗 ---
class RefineWindow(QDialog):
    def __init__(self, parent, program_data):
        super().__init__(parent)
        self.setWindowTitle(f"详情: {program_data['name']}"); self.resize(800, 600)
        self.program_data = program_data; self.all_exes = program_data['all_exes']
        self.original_selection = set(program_data['selected_exes']); self.icon_provider = QFileIconProvider()
        self.build_ui(); self.populate_tree(); self.pre_select_items(); self.on_filter_changed()

    def build_ui(self):
        layout = QVBoxLayout(self); layout.setSpacing(10)
        fl = QHBoxLayout(); fl.addWidget(QLabel("🔍 搜索:")); self.filter_edit = QLineEdit()
        self.filter_edit.setPlaceholderText("输入文件名过滤..."); self.filter_edit.textChanged.connect(self.on_filter_changed)
        fl.addWidget(self.filter_edit); layout.addLayout(fl)
        self.tree = QTreeWidget(); self.tree.setHeaderLabels(['程序名', '大小', '完整路径'])
        self.tree.setSelectionMode(QTreeWidget.SelectionMode.ExtendedSelection)
        self.tree.setSortingEnabled(True); self.tree.setAlternatingRowColors(True)
        layout.addWidget(self.tree)
        bl = QHBoxLayout()
        btn_all = QPushButton("全选可见"); btn_all.clicked.connect(self.select_all_visible)
        btn_none = QPushButton("清空选择"); btn_none.clicked.connect(self.select_none)
        self.btn_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.btn_box.accepted.connect(self.on_ok); self.btn_box.rejected.connect(self.reject)
        bl.addWidget(btn_all); bl.addWidget(btn_none); bl.addStretch(); bl.addWidget(self.btn_box); layout.addLayout(bl)

    def populate_tree(self):
        self.tree.setSortingEnabled(False); items = []
        for (full_path, file_name, size_bytes, rel_path) in self.all_exes:
            item = QTreeWidgetItem([file_name, f"{size_bytes/1024/1024:.2f} MB", full_path])
            item.setIcon(0, self.icon_provider.icon(QFileInfo(full_path)))
            item.setData(0, Qt.ItemDataRole.UserRole, full_path); items.append(item)
        self.tree.addTopLevelItems(items); self.tree.setSortingEnabled(True)
        self.tree.header().resizeSections(QHeaderView.ResizeMode.ResizeToContents)

    def pre_select_items(self):
        for item in self.tree.findItems("", Qt.MatchFlag.MatchContains | Qt.MatchFlag.MatchRecursive, 0):
            if item.data(0, Qt.ItemDataRole.UserRole) in self.original_selection: item.setSelected(True)
    def on_filter_changed(self):
        q = self.filter_edit.text().lower()
        for i in range(self.tree.topLevelItemCount()):
            item = self.tree.topLevelItem(i)
            item.setHidden(q not in item.text(0).lower() and q not in item.text(2).lower())
    def select_all_visible(self):
        for i in range(self.tree.topLevelItemCount()):
            if not self.tree.topLevelItem(i).isHidden(): self.tree.topLevelItem(i).setSelected(True)
    def select_none(self): self.tree.clearSelection()
    def on_ok(self):
        self.program_data['selected_exes'] = tuple([i.data(0, Qt.ItemDataRole.UserRole) for i in self.tree.selectedItems()])
        self.accept()

# --- 扫描页面类 ---
class ScanPage(QWidget):
    sig_log = Signal(str); sig_status = Signal(str)
    def __init__(self):
        super().__init__()
        self.config = backend.load_config(); self.programs = []
        self.scan_thread = None; self.scan_worker = None; self.icon_provider = QFileIconProvider()
        self.build_ui()

    def build_ui(self):
        layout = QVBoxLayout(self); layout.setContentsMargins(30, 30, 30, 30); layout.setSpacing(15)
        top_box = QHBoxLayout()
        self.path_edit = QLineEdit(); self.path_edit.setReadOnly(True); self.path_edit.setPlaceholderText("请选择要扫描的根目录...")
        btn_browse = QPushButton("📂 选择目录"); btn_browse.clicked.connect(self.browse_scan_path)
        top_box.addWidget(self.path_edit); top_box.addWidget(btn_browse); layout.addLayout(top_box)

        self.btn_action = QPushButton("🚀 开始扫描"); self.btn_action.setObjectName("primaryButton")
        self.btn_action.setMinimumHeight(45); self.btn_action.setEnabled(False); self.btn_action.clicked.connect(self.toggle_scan)
        layout.addWidget(self.btn_action); layout.addSpacing(10)

        header_frame = QHBoxLayout()
        self.chk_select_all = QCheckBox("全选所有发现的程序")
        self.chk_select_all.stateChanged.connect(self.toggle_select_all)
        self.lbl_count = QLabel("已选 0 / 共 0 个"); self.lbl_count.setStyleSheet("font-weight: bold; color: #0078D7;")
        header_frame.addWidget(self.chk_select_all); header_frame.addStretch(); header_frame.addWidget(self.lbl_count)
        layout.addLayout(header_frame)

        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(['程序名称', '推荐执行文件', '所在目录'])
        self.tree.setAlternatingRowColors(True); self.tree.setIconSize(QSize(24, 24))
        self.tree.itemDoubleClicked.connect(self.open_refine)
        self.tree.itemChanged.connect(self.on_tree_item_changed)
        layout.addWidget(self.tree)

        footer_layout = QVBoxLayout(); footer_layout.setSpacing(5)
        self.lbl_path_hint = QLabel("")
        self.lbl_path_hint.setAlignment(Qt.AlignmentFlag.AlignRight); self.lbl_path_hint.setStyleSheet("color: #999999; font-size: 9pt;")
        self.btn_gen = QPushButton("✨ 生成选中快捷方式"); self.btn_gen.setObjectName("primaryButton")
        self.btn_gen.setMinimumHeight(40); self.btn_gen.setEnabled(False); self.btn_gen.clicked.connect(self.generate)
        footer_layout.addWidget(self.lbl_path_hint); footer_layout.addWidget(self.btn_gen)
        layout.addLayout(footer_layout)

        last = self.config.get('Settings', 'last_scan_path', fallback='')
        if last: self.path_edit.setText(last); self.btn_action.setEnabled(True)

    def update_path_hint(self, path):
        if not path: path = os.path.join(os.path.expanduser('~'), 'Desktop', backend.DEFAULT_OUTPUT_FOLDER_NAME)
        self.lbl_path_hint.setText(f"将生成至: {path}")

    def toggle_select_all(self, state):
        is_checked = (state == Qt.CheckState.Checked.value)
        self.tree.blockSignals(True)
        root = self.tree.invisibleRootItem()
        for i in range(root.childCount()):
            root.child(i).setCheckState(0, Qt.CheckState.Checked if is_checked else Qt.CheckState.Unchecked)
        self.tree.blockSignals(False)
        self.update_selection_count()

    def on_tree_item_changed(self, item, column):
        if column == 0: self.update_selection_count()

    def update_selection_count(self):
        total = self.tree.topLevelItemCount(); checked = 0; root = self.tree.invisibleRootItem()
        for i in range(total):
            if root.child(i).checkState(0) == Qt.CheckState.Checked: checked += 1
        self.lbl_count.setText(f"已选 {checked} / 共 {total} 个")
        self.chk_select_all.blockSignals(True)
        if total > 0 and checked == total: self.chk_select_all.setCheckState(Qt.CheckState.Checked)
        elif checked == 0: self.chk_select_all.setCheckState(Qt.CheckState.Unchecked)
        else: self.chk_select_all.setCheckState(Qt.CheckState.PartiallyChecked)
        self.chk_select_all.blockSignals(False)

    def browse_scan_path(self):
        d = QFileDialog.getExistingDirectory(self, "选择目录", self.path_edit.text())
        if d: self.path_edit.setText(d); self.btn_action.setEnabled(True)

    def toggle_scan(self):
        if self.scan_thread and self.scan_thread.isRunning():
            self.scan_worker.stop(); self.btn_action.setText("正在停止..."); self.btn_action.setEnabled(False); return
        path = self.path_edit.text()
        self.btn_action.setText("🛑 停止扫描"); self.btn_action.setObjectName("stopButton"); self.btn_action.setStyle(self.style())
        self.btn_gen.setEnabled(False); self.tree.clear();
        self.sig_status.emit(f"正在扫描: {path} ...")
        self.chk_select_all.setCheckState(Qt.CheckState.Checked); self.lbl_count.setText("扫描中...")

        self.scan_thread = QThread(self); self.scan_worker = ScanWorker(path)
        self.scan_worker.moveToThread(self.scan_thread)
        self.scan_worker.log.connect(self.sig_log); self.scan_worker.finished.connect(self.on_scan_done)
        self.scan_thread.started.connect(self.scan_worker.run); self.scan_worker.finished.connect(self.scan_thread.quit)
        self.scan_thread.finished.connect(self.cleanup_thread); self.scan_thread.start()

    @Slot(list)
    def on_scan_done(self, res):
        self.programs = res; self.populate_tree()
        self.sig_status.emit(f"就绪 - 共发现 {len(res)} 个程序")
        self.btn_action.setText("🚀 开始扫描"); self.btn_action.setObjectName("primaryButton"); self.btn_action.setStyle(self.style())
        self.btn_action.setEnabled(True); self.btn_gen.setEnabled(len(res) > 0)
        self.update_selection_count()

    @Slot()
    def cleanup_thread(self):
        if self.scan_thread: self.scan_thread.deleteLater()
        if self.scan_worker: self.scan_worker.deleteLater()
        self.scan_thread = None; self.scan_worker = None

    def populate_tree(self):
        self.tree.clear(); self.tree.blockSignals(True); items = []
        for i, p in enumerate(self.programs):
            target = p['selected_exes'][0] if p['selected_exes'] else ""
            name_disp = os.path.basename(target) if target else "未选择"
            item = QTreeWidgetItem([p['name'], name_disp, p['root_path']])
            item.setCheckState(0, Qt.CheckState.Checked); item.setToolTip(2, p['root_path'])
            if target: item.setIcon(1, self.icon_provider.icon(QFileInfo(target))); item.setToolTip(1, target)
            item.setData(0, Qt.ItemDataRole.UserRole, i); items.append(item)
        self.tree.addTopLevelItems(items); self.tree.header().resizeSections(QHeaderView.ResizeMode.ResizeToContents); self.tree.blockSignals(False)

    def open_refine(self, item):
        idx = item.data(0, Qt.ItemDataRole.UserRole); prog = self.programs[idx]
        if RefineWindow(self, prog).exec() == QDialog.DialogCode.Accepted:
            target = prog['selected_exes'][0] if prog['selected_exes'] else ""
            item.setText(1, os.path.basename(target))
            if target: item.setIcon(1, self.icon_provider.icon(QFileInfo(target)))

    def generate(self):
        conf = backend.load_config()
        out = conf.get('Settings', 'output_path', fallback='').strip()
        if not out: out = os.path.join(os.path.expanduser('~'), 'Desktop', backend.DEFAULT_OUTPUT_FOLDER_NAME)
        if not os.path.exists(out): os.makedirs(out)
        cnt = 0; root = self.tree.invisibleRootItem()
        for i in range(root.childCount()):
            item = root.child(i)
            if item.checkState(0) == Qt.CheckState.Checked:
                idx = item.data(0, Qt.ItemDataRole.UserRole); p = self.programs[idx]
                for exe in p['selected_exes']:
                    name = os.path.splitext(os.path.basename(exe))[0]
                    if backend.create_shortcut(exe, os.path.join(out, f"{name}.lnk"))[0]: cnt +=1
        QMessageBox.information(self, "完成", f"成功创建 {cnt} 个快捷方式！\n目录: {out}")

    def save_state(self):
        self.config['Settings']['last_scan_path'] = self.path_edit.text()
        backend.save_config(self.config)
        if self.scan_thread: self.scan_worker.stop(); self.scan_thread.wait(1000)