import sys
import os
import re

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QFrame, QFileDialog, QLineEdit, QLabel, QTreeWidget,
    QTreeWidgetItem, QHeaderView, QDialog, QDialogButtonBox,
    QMessageBox, QTextEdit, QStackedWidget, QButtonGroup, QComboBox,
    QFileIconProvider, QStyle, QStatusBar, QProgressBar, QSplitter
)
from PySide6.QtCore import Qt, QSize, QObject, Signal, Slot, QThread, QFileInfo
from PySide6.QtGui import QCloseEvent, QIcon

import scanner_backend as backend
import scanner_styles as styles


# --- 线程类 (保持不变) ---
class ScanWorker(QObject):
    finished = Signal(list);
    log = Signal(str)

    def __init__(self, scan_path, blocklist, ignored_dirs):
        super().__init__()
        self.scan_path = scan_path;
        self.blocklist = blocklist;
        self.ignored_dirs = ignored_dirs;
        self.is_running = True

    @Slot()
    def stop(self):
        self.is_running = False

    @Slot()
    def run(self):
        try:
            programs = backend.discover_programs(self.scan_path, self.blocklist, self.ignored_dirs, self.log.emit,
                                                 lambda: not self.is_running)
            self.finished.emit(programs)
        except Exception as e:
            self.log.emit(f"Error: {e}");
            self.finished.emit([])


# --- 详情弹窗 (保持不变) ---
class RefineWindow(QDialog):
    def __init__(self, parent, program_data):
        super().__init__(parent)
        self.setWindowTitle(f"详情: {program_data['name']}")
        self.resize(800, 600);
        self.program_data = program_data;
        self.all_exes = program_data['all_exes']
        self.original_selection = set(program_data['selected_exes']);
        self.icon_provider = QFileIconProvider()
        self.build_ui();
        self.populate_tree();
        self.pre_select_items();
        self.on_filter_changed()

    def build_ui(self):
        layout = QVBoxLayout(self);
        layout.setSpacing(10)
        fl = QHBoxLayout();
        fl.addWidget(QLabel("🔍 搜索:"));
        self.filter_edit = QLineEdit()
        self.filter_edit.setPlaceholderText("输入文件名过滤...");
        self.filter_edit.textChanged.connect(self.on_filter_changed)
        fl.addWidget(self.filter_edit);
        layout.addLayout(fl)
        self.tree = QTreeWidget();
        self.tree.setHeaderLabels(['程序名', '大小', '完整路径'])
        self.tree.setSelectionMode(QTreeWidget.SelectionMode.ExtendedSelection)
        self.tree.setSortingEnabled(True);
        self.tree.setAlternatingRowColors(True)
        layout.addWidget(self.tree)
        bl = QHBoxLayout()
        btn_all = QPushButton("全选可见");
        btn_all.clicked.connect(self.select_all_visible)
        btn_none = QPushButton("清空选择");
        btn_none.clicked.connect(self.select_none)
        self.btn_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.btn_box.accepted.connect(self.on_ok);
        self.btn_box.rejected.connect(self.reject)
        bl.addWidget(btn_all);
        bl.addWidget(btn_none);
        bl.addStretch();
        bl.addWidget(self.btn_box);
        layout.addLayout(bl)

    def populate_tree(self):
        self.tree.setSortingEnabled(False)
        items = []
        for (full_path, file_name, size_bytes, rel_path) in self.all_exes:
            item = QTreeWidgetItem([file_name, f"{size_bytes / 1024 / 1024:.2f} MB", full_path])
            item.setIcon(0, self.icon_provider.icon(QFileInfo(full_path)))
            item.setData(0, Qt.ItemDataRole.UserRole, full_path);
            items.append(item)
        self.tree.addTopLevelItems(items);
        self.tree.setSortingEnabled(True)
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

    def select_none(self):
        self.tree.clearSelection()

    def on_ok(self):
        self.program_data['selected_exes'] = tuple(
            [i.data(0, Qt.ItemDataRole.UserRole) for i in self.tree.selectedItems()])
        self.accept()


# --- 主窗口 ---
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("快捷方式扫描器 (Beta 4.1)")
        self.config = backend.load_config()
        self.programs = []
        self.blocklist, msg1 = backend.load_blocklist();
        self.ignored_dirs, msg2 = backend.load_ignored_dirs()
        self.scan_thread = None;
        self.scan_worker = None;
        self.icon_provider = QFileIconProvider()
        self.build_ui();
        self.setup_statusbar();
        self.load_settings()
        self.log_to_settings(f"系统初始化...\n{msg1}\n{msg2}")

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
        self.nav_scan = add_nav("  扫描程序", QStyle.StandardPixmap.SP_ComputerIcon, 0)
        self.nav_filter = add_nav("  过滤规则", QStyle.StandardPixmap.SP_MessageBoxWarning, 1)
        self.nav_set = add_nav("  系统设置", QStyle.StandardPixmap.SP_FileDialogDetailedView, 2)
        sb_layout.addStretch()
        ver_lbl = QLabel("Beta 4.1");
        ver_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ver_lbl.setStyleSheet("color: #888888; font-size: 9pt;");
        sb_layout.addWidget(ver_lbl)
        root_layout.addWidget(sidebar)

        # Content
        self.stack = QStackedWidget();
        self.stack.setObjectName("mainArea")
        self.stack.addWidget(self.view_scanner())
        self.stack.addWidget(self.view_filters())
        self.stack.addWidget(self.view_settings())
        root_layout.addWidget(self.stack)
        self.nav_group.idClicked.connect(self.stack.setCurrentIndex)
        self.nav_scan.setChecked(True)

    def view_scanner(self):
        page = QWidget();
        layout = QVBoxLayout(page);
        layout.setContentsMargins(30, 30, 30, 30);
        layout.setSpacing(20)
        top_box = QHBoxLayout()
        self.path_edit = QLineEdit();
        self.path_edit.setReadOnly(True);
        self.path_edit.setPlaceholderText("请选择要扫描的根目录...")
        btn_browse = QPushButton("📂 选择目录");
        btn_browse.clicked.connect(self.browse_scan_path)
        top_box.addWidget(self.path_edit);
        top_box.addWidget(btn_browse);
        layout.addLayout(top_box)

        self.btn_action = QPushButton("🚀 开始扫描");
        self.btn_action.setObjectName("primaryButton")
        self.btn_action.setMinimumHeight(45);
        self.btn_action.setEnabled(False);
        self.btn_action.clicked.connect(self.toggle_scan)
        layout.addWidget(self.btn_action)

        info_box = QHBoxLayout()
        info_box.addWidget(QLabel("📝 发现结果 (勾选以生成，双击以修改)"))
        info_box.addStretch();
        self.lbl_count = QLabel("0 个程序");
        info_box.addWidget(self.lbl_count)
        layout.addLayout(info_box)

        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(['程序名称', '推荐执行文件', '所在目录'])
        self.tree.setAlternatingRowColors(True)
        self.tree.itemDoubleClicked.connect(self.open_refine)
        # 【Beta 4.1】 启用图标尺寸优化和工具提示
        self.tree.setIconSize(QSize(24, 24))
        layout.addWidget(self.tree)

        gen_box = QHBoxLayout();
        gen_box.addStretch()
        self.btn_gen = QPushButton("✨ 生成选中快捷方式");
        self.btn_gen.setObjectName("primaryButton")
        self.btn_gen.setMinimumHeight(40);
        self.btn_gen.setEnabled(False);
        self.btn_gen.clicked.connect(self.generate)
        gen_box.addWidget(self.btn_gen);
        layout.addLayout(gen_box)
        return page

    def view_filters(self):
        page = QWidget();
        layout = QVBoxLayout(page);
        layout.setContentsMargins(30, 30, 30, 30);
        layout.setSpacing(20)
        layout.addWidget(QLabel("🛡️ 过滤规则管理 (编辑后请保存)"), 0, Qt.AlignmentFlag.AlignBottom)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        w1 = QWidget();
        l1 = QVBoxLayout(w1);
        l1.setContentsMargins(0, 0, 10, 0)
        l1.addWidget(QLabel("文件黑名单 (.exe)"));
        l1.addWidget(QLabel("跳过包含这些关键词的文件"))
        self.blk_edit = QTextEdit();
        self.blk_edit.setPlainText("\n".join(sorted(self.blocklist)));
        l1.addWidget(self.blk_edit)
        splitter.addWidget(w1)
        w2 = QWidget();
        l2 = QVBoxLayout(w2);
        l2.setContentsMargins(10, 0, 0, 0)
        l2.addWidget(QLabel("黑洞目录 (Dir)"));
        l2.addWidget(QLabel("完全跳过这些目录 (及其子目录)"))
        self.ign_edit = QTextEdit();
        self.ign_edit.setPlainText("\n".join(sorted(self.ignored_dirs)));
        l2.addWidget(self.ign_edit)
        splitter.addWidget(w2)
        layout.addWidget(splitter, 1)
        btn_save = QPushButton("💾 保存所有规则");
        btn_save.setObjectName("primaryButton");
        btn_save.clicked.connect(self.save_rules)
        layout.addWidget(btn_save, 0, Qt.AlignmentFlag.AlignRight)
        return page

    def view_settings(self):
        page = QWidget();
        layout = QVBoxLayout(page);
        layout.setContentsMargins(30, 30, 30, 30);
        layout.setSpacing(20)
        g1 = QFrame();
        l1 = QVBoxLayout(g1);
        l1.addWidget(QLabel("🎨 界面风格"))
        self.theme_combo = QComboBox();
        self.theme_combo.addItems(["暗黑模式 (Dark)", "明亮模式 (Light)"])
        self.theme_combo.currentIndexChanged.connect(self.apply_theme);
        l1.addWidget(self.theme_combo);
        layout.addWidget(g1)
        g2 = QFrame();
        l2 = QVBoxLayout(g2);
        l2.addWidget(QLabel("💾 输出路径"))
        hb = QHBoxLayout();
        self.out_edit = QLineEdit();
        self.out_edit.setPlaceholderText("默认桌面")
        btn_out = QPushButton("浏览...");
        btn_out.clicked.connect(self.browse_out_path)
        hb.addWidget(self.out_edit);
        hb.addWidget(btn_out);
        l2.addLayout(hb);
        layout.addWidget(g2)
        layout.addWidget(QLabel("📜 运行日志"));
        self.log_view = QTextEdit();
        self.log_view.setReadOnly(True);
        self.log_view.setObjectName("logArea")
        layout.addWidget(self.log_view)
        return page

    # --- Logic ---
    def browse_scan_path(self):
        d = QFileDialog.getExistingDirectory(self, "选择目录", self.path_edit.text())
        if d: self.path_edit.setText(d); self.btn_action.setEnabled(True)

    def browse_out_path(self):
        d = QFileDialog.getExistingDirectory(self, "选择目录", self.out_edit.text())
        if d: self.out_edit.setText(d)

    def toggle_scan(self):
        if self.scan_thread and self.scan_thread.isRunning():
            self.scan_worker.stop();
            self.btn_action.setText("正在停止...");
            self.btn_action.setEnabled(False);
            return
        path = self.path_edit.text()
        self.btn_action.setText("🛑 停止扫描");
        self.btn_action.setObjectName("stopButton");
        self.btn_action.setStyle(self.style())
        self.btn_gen.setEnabled(False);
        self.tree.clear();
        self.progress.setVisible(True)
        self.status_label.setText(f"正在扫描: {path} ...")
        self.scan_thread = QThread(self);
        self.scan_worker = ScanWorker(path, self.blocklist, self.ignored_dirs)
        self.scan_worker.moveToThread(self.scan_thread)
        self.scan_worker.log.connect(self.on_log);
        self.scan_worker.finished.connect(self.on_scan_done)
        self.scan_thread.started.connect(self.scan_worker.run);
        self.scan_worker.finished.connect(self.scan_thread.quit)
        self.scan_thread.finished.connect(self.cleanup_thread);
        self.scan_thread.start()

    @Slot(str)
    def on_log(self, msg):
        self.log_to_settings(msg)
        if "发现" in msg: self.status_label.setText(msg)

    @Slot(list)
    def on_scan_done(self, res):
        self.programs = res;
        self.populate_tree();
        self.progress.setVisible(False)
        self.status_label.setText(f"就绪 - 共发现 {len(res)} 个程序");
        self.lbl_count.setText(f"{len(res)} 个程序")
        self.btn_action.setText("🚀 开始扫描");
        self.btn_action.setObjectName("primaryButton");
        self.btn_action.setStyle(self.style())
        self.btn_action.setEnabled(True);
        self.btn_gen.setEnabled(len(res) > 0)

    @Slot()
    def cleanup_thread(self):
        if self.scan_thread: self.scan_thread.deleteLater()
        if self.scan_worker: self.scan_worker.deleteLater()
        self.scan_thread = None;
        self.scan_worker = None

    def populate_tree(self):
        self.tree.clear()
        items = []
        for i, p in enumerate(self.programs):
            target = p['selected_exes'][0] if p['selected_exes'] else ""
            name_disp = os.path.basename(target) if target else "未选择"

            item = QTreeWidgetItem([p['name'], name_disp, p['root_path']])

            # 【Beta 4.1】 功能：复选框 + 图标移位 + 工具提示
            item.setCheckState(0, Qt.CheckState.Checked)  # 默认勾选
            item.setToolTip(2, p['root_path'])  # 路径提示

            if target:
                item.setIcon(1, self.icon_provider.icon(QFileInfo(target)))  # 图标在第2列
                item.setToolTip(1, target)

            item.setData(0, Qt.ItemDataRole.UserRole, i)
            items.append(item)
        self.tree.addTopLevelItems(items)
        self.tree.header().resizeSections(QHeaderView.ResizeMode.ResizeToContents)

    def open_refine(self, item):
        idx = item.data(0, Qt.ItemDataRole.UserRole);
        prog = self.programs[idx]
        if RefineWindow(self, prog).exec() == QDialog.DialogCode.Accepted:
            target = prog['selected_exes'][0] if prog['selected_exes'] else ""
            item.setText(1, os.path.basename(target))
            if target: item.setIcon(1, self.icon_provider.icon(QFileInfo(target)))

    def generate(self):
        out = self.out_edit.text() or os.path.join(os.path.expanduser('~'), 'Desktop',
                                                   backend.DEFAULT_OUTPUT_FOLDER_NAME)
        if not os.path.exists(out): os.makedirs(out)
        cnt = 0

        # 【Beta 4.1】 只生成勾选的项目
        root = self.tree.invisibleRootItem()
        for i in range(root.childCount()):
            item = root.child(i)
            if item.checkState(0) == Qt.CheckState.Checked:
                idx = item.data(0, Qt.ItemDataRole.UserRole)
                p = self.programs[idx]
                for exe in p['selected_exes']:
                    name = os.path.splitext(os.path.basename(exe))[0]
                    if backend.create_shortcut(exe, os.path.join(out, f"{name}.lnk"))[0]: cnt += 1

        QMessageBox.information(self, "完成", f"成功创建 {cnt} 个快捷方式！\n目录: {out}")

    def log_to_settings(self, m):
        self.log_view.append(m)

    def apply_theme(self, idx):
        self.config['Settings']['theme'] = 'light' if idx == 1 else 'dark'
        QApplication.instance().setStyleSheet(styles.LIGHT_QSS if idx == 1 else styles.DARK_QSS)

    def save_rules(self):
        blk = {l.strip().lower() for l in self.blk_edit.toPlainText().split('\n') if l.strip()}
        ign = {l.strip() for l in self.ign_edit.toPlainText().split('\n') if l.strip()}
        backend.save_blocklist(blk);
        backend.save_ignored_dirs(ign)
        self.blocklist = blk;
        self.ignored_dirs = ign
        QMessageBox.information(self, "成功", "所有过滤规则已保存。")

    def load_settings(self):
        last = self.config.get('Settings', 'last_scan_path', fallback='')
        if last: self.path_edit.setText(last); self.btn_action.setEnabled(True)
        self.out_edit.setText(self.config.get('Settings', 'output_path', fallback=''))
        theme = self.config.get('Settings', 'theme', fallback='dark')
        self.theme_combo.setCurrentIndex(1 if theme == 'light' else 0)
        self.apply_theme(self.theme_combo.currentIndex())

    def closeEvent(self, e):
        self.config['Settings']['last_scan_path'] = self.path_edit.text()
        self.config['Settings']['output_path'] = self.out_edit.text()
        geo = self.geometry();
        self.config['Settings']['window_geometry'] = f"{geo.width()}x{geo.height()}+{geo.x()}+{geo.y()}"
        backend.save_config(self.config)
        if self.scan_thread: self.scan_worker.stop(); self.scan_thread.wait(1000)
        e.accept()


if __name__ == "__main__":
    if hasattr(Qt, 'AA_EnableHighDpiScaling'): QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    app = QApplication(sys.argv);
    app.setStyleSheet(styles.DARK_QSS)
    win = MainWindow();
    win.show();
    sys.exit(app.exec())