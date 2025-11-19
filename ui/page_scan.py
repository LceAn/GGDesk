from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLineEdit, QLabel,
    QTreeWidget, QTreeWidgetItem, QHeaderView, QDialog, QDialogButtonBox,
    QCheckBox, QFileDialog, QMessageBox, QFileIconProvider, QFrame, QGroupBox
)
from PySide6.QtCore import Qt, Signal, Slot, QThread, QObject, QSize, QFileInfo
from PySide6.QtGui import QIcon, QColor, QBrush
import os
import scanner_backend as backend


class ScanWorker(QObject):
    finished = Signal(list);
    log = Signal(str)

    def __init__(self, sources, custom_path):
        super().__init__()
        self.sources = sources;
        self.custom_path = custom_path;
        self.is_running = True

    @Slot()
    def stop(self):
        self.is_running = False

    @Slot()
    def run(self):
        try:
            blk, _ = backend.load_blocklist();
            ign, _ = backend.load_ignored_dirs()
            programs = backend.discover_programs(self.sources, self.custom_path, blk, ign, self.log.emit,
                                                 lambda: not self.is_running)
            self.finished.emit(programs)
        except Exception as e:
            self.log.emit(f"Error: {e}");
            self.finished.emit([])


class RefineWindow(QDialog):
    def __init__(self, parent, program_data):
        super().__init__(parent)
        self.setWindowTitle(f"详情修改");
        self.resize(850, 650)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self.program_data = program_data;
        self.all_exes = program_data.get('all_exes', [])
        self.original_selection = set(program_data['selected_exes']);
        self.icon_provider = QFileIconProvider()
        self.build_ui()
        if self.all_exes:
            self.populate_tree(); self.pre_select_items(); self.on_filter_changed(); self.update_count_label()
        else:
            self.lbl_count.setText("此类型的程序不支持修改执行文件。"); self.tree.setEnabled(False)

    def build_ui(self):
        layout = QVBoxLayout(self);
        layout.setContentsMargins(0, 0, 0, 0);
        layout.setSpacing(0)
        header_widget = QWidget();
        header_widget.setStyleSheet("background-color: #F5F7FA; border-bottom: 1px solid #E0E0E0;")
        header_layout = QHBoxLayout(header_widget);
        header_layout.setContentsMargins(20, 15, 20, 15);
        header_layout.setSpacing(15)
        lbl_prog_name = QLabel(self.program_data['name']);
        lbl_prog_name.setStyleSheet("font-size: 14pt; font-weight: bold; color: #333;")
        lbl_prog_path = QLabel(f"📂 {self.program_data.get('root_path', '')}");
        lbl_prog_path.setStyleSheet("color: #888; font-size: 9pt;")
        header_layout.addWidget(lbl_prog_name);
        header_layout.addWidget(lbl_prog_path);
        header_layout.addStretch()
        layout.addWidget(header_widget)

        content_widget = QWidget();
        content_layout = QVBoxLayout(content_widget);
        content_layout.setContentsMargins(20, 15, 20, 15);
        content_layout.setSpacing(10)
        search_layout = QHBoxLayout();
        search_layout.addWidget(QLabel("🔍"))
        self.filter_edit = QLineEdit();
        self.filter_edit.setPlaceholderText("输入文件名过滤 (例如: .exe)")
        self.filter_edit.textChanged.connect(self.on_filter_changed)
        search_layout.addWidget(self.filter_edit);
        content_layout.addLayout(search_layout)
        self.tree = QTreeWidget();
        self.tree.setHeaderLabels(['程序名', '大小', '完整路径'])
        self.tree.setSelectionMode(QTreeWidget.SelectionMode.ExtendedSelection);
        self.tree.setSortingEnabled(True)
        self.tree.setAlternatingRowColors(True);
        self.tree.setIconSize(QSize(20, 20))
        self.tree.setStyleSheet("QTreeWidget { border: 1px solid #CCCCCC; border-radius: 4px; }")
        self.tree.itemDoubleClicked.connect(self.on_item_double_clicked)
        self.tree.itemSelectionChanged.connect(self.update_count_label)
        content_layout.addWidget(self.tree)

        bottom_bar = QHBoxLayout()
        btn_all = QPushButton("全选可见");
        btn_all.setCursor(Qt.PointingHandCursor);
        btn_all.clicked.connect(self.select_all_visible)
        btn_none = QPushButton("清空选择");
        btn_none.setCursor(Qt.PointingHandCursor);
        btn_none.clicked.connect(self.select_none)
        self.lbl_count = QLabel("已选 0 / 共 0 个");
        self.lbl_count.setStyleSheet("color: #0078D7; font-weight: bold; margin-left: 10px;")
        bottom_bar.addWidget(btn_all);
        bottom_bar.addWidget(btn_none);
        bottom_bar.addWidget(self.lbl_count);
        bottom_bar.addStretch()
        self.btn_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.btn_box.accepted.connect(self.on_ok);
        self.btn_box.rejected.connect(self.reject)
        bottom_bar.addWidget(self.btn_box);
        content_layout.addLayout(bottom_bar)
        layout.addWidget(content_widget)

    def populate_tree(self):
        self.tree.setSortingEnabled(False);
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
        self.tree.blockSignals(True)
        for item in self.tree.findItems("", Qt.MatchFlag.MatchContains | Qt.MatchFlag.MatchRecursive, 0):
            if item.data(0, Qt.ItemDataRole.UserRole) in self.original_selection: item.setSelected(True)
        self.tree.blockSignals(False)

    def update_count_label(self):
        selected_count = len(self.tree.selectedItems());
        total_visible = 0;
        root = self.tree.invisibleRootItem()
        for i in range(root.childCount()):
            if not root.child(i).isHidden(): total_visible += 1
        self.lbl_count.setText(f"已选 {selected_count} / 可见 {total_visible} (共 {root.childCount()})")

    def on_filter_changed(self):
        q = self.filter_edit.text().lower()
        for i in range(self.tree.topLevelItemCount()):
            item = self.tree.topLevelItem(i)
            hidden = not (q in item.text(0).lower() or q in item.text(2).lower())
            item.setHidden(hidden)
        self.update_count_label()

    def on_item_double_clicked(self, item, column):
        item.setSelected(not item.isSelected())

    def select_all_visible(self):
        for i in range(self.tree.topLevelItemCount()):
            if not self.tree.topLevelItem(i).isHidden(): self.tree.topLevelItem(i).setSelected(True)

    def select_none(self):
        self.tree.clearSelection()

    def on_ok(self):
        self.program_data['selected_exes'] = tuple(
            [i.data(0, Qt.ItemDataRole.UserRole) for i in self.tree.selectedItems()])
        self.accept()


class GenSuccessDialog(QDialog):
    def __init__(self, parent, count, output_path):
        super().__init__(parent)
        self.output_path = output_path
        self.setWindowTitle("生成完成");
        self.setMinimumWidth(420)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        layout = QVBoxLayout(self);
        layout.setContentsMargins(20, 20, 20, 20);
        layout.setSpacing(15)
        h_box = QHBoxLayout();
        icon_label = QLabel("✅");
        icon_label.setStyleSheet("font-size: 32px;")
        h_box.addWidget(icon_label)
        title_box = QVBoxLayout();
        lbl_title = QLabel("快捷方式生成成功！");
        lbl_title.setStyleSheet("font-size: 12pt; font-weight: bold; color: #2E8B57;")
        lbl_desc = QLabel(f"共成功创建 <b>{count}</b> 个快捷方式。");
        title_box.addWidget(lbl_title);
        title_box.addWidget(lbl_desc);
        h_box.addLayout(title_box);
        h_box.addStretch()
        layout.addLayout(h_box)
        line = QFrame();
        line.setFrameShape(QFrame.Shape.HLine);
        line.setFrameShadow(QFrame.Shadow.Sunken);
        line.setStyleSheet("color: #DDDDDD;");
        layout.addWidget(line)
        layout.addWidget(QLabel("保存位置:"))
        path_edit = QLineEdit(output_path);
        path_edit.setReadOnly(True);
        path_edit.setStyleSheet("background-color: transparent; border: none; color: #666666;");
        layout.addWidget(path_edit)
        btn_layout = QHBoxLayout();
        btn_layout.addStretch()
        self.btn_open = QPushButton("📂 打开生成目录");
        self.btn_open.setObjectName("primaryButton");
        self.btn_open.setCursor(Qt.PointingHandCursor);
        self.btn_open.setMinimumHeight(35);
        self.btn_open.clicked.connect(self.on_open)
        self.btn_close = QPushButton("关闭");
        self.btn_close.setMinimumHeight(35);
        self.btn_close.clicked.connect(self.accept)
        btn_layout.addWidget(self.btn_open);
        btn_layout.addWidget(self.btn_close);
        layout.addLayout(btn_layout)

    def on_open(self): backend.open_file_explorer(self.output_path); self.accept()


class ScanPage(QWidget):
    sig_log = Signal(str);
    sig_status = Signal(str)

    def __init__(self):
        super().__init__()
        self.config = backend.load_config()
        self.programs = []
        self.scan_thread = None;
        self.scan_worker = None;
        self.icon_provider = QFileIconProvider()
        self.build_ui()
        self.update_rules_summary()

    def build_ui(self):
        layout = QVBoxLayout(self);
        layout.setContentsMargins(30, 30, 30, 30);
        layout.setSpacing(15)

        self.lbl_rules_summary = QLabel("规则加载中...")
        self.lbl_rules_summary.setStyleSheet(
            "background-color: #FFF8E1; color: #E65100; border: 1px solid #FFE082; border-radius: 4px; padding: 6px; font-size: 9pt;")
        layout.addWidget(self.lbl_rules_summary)

        src_group = QGroupBox("选择扫描范围")
        src_layout = QHBoxLayout(src_group)
        self.chk_start_menu = QCheckBox("开始菜单 (Start Menu)");
        self.chk_start_menu.setChecked(True)
        self.chk_uwp = QCheckBox("应用商店 (UWP)");
        self.chk_uwp.setChecked(True)
        self.chk_custom = QCheckBox("自定义目录");
        self.chk_custom.setChecked(True);
        self.chk_custom.toggled.connect(self.toggle_custom_path)
        src_layout.addWidget(self.chk_start_menu);
        src_layout.addWidget(self.chk_uwp);
        src_layout.addWidget(self.chk_custom);
        src_layout.addStretch()
        layout.addWidget(src_group)

        self.path_box = QWidget()
        pb_layout = QHBoxLayout(self.path_box);
        pb_layout.setContentsMargins(0, 0, 0, 0)
        self.path_edit = QLineEdit();
        self.path_edit.setReadOnly(True);
        self.path_edit.setPlaceholderText("请选择要扫描的根目录...")
        btn_browse = QPushButton("📂 选择目录");
        btn_browse.clicked.connect(self.browse_scan_path)
        pb_layout.addWidget(self.path_edit);
        pb_layout.addWidget(btn_browse)
        layout.addWidget(self.path_box)

        self.btn_action = QPushButton("🚀 开始扫描");
        self.btn_action.setObjectName("primaryButton")
        self.btn_action.setMinimumHeight(45);
        self.btn_action.clicked.connect(self.toggle_scan)
        layout.addWidget(self.btn_action);
        layout.addSpacing(5)

        info_frame = QFrame();
        info_frame.setObjectName("infoFrame")
        info_frame.setStyleSheet(
            "QFrame#infoFrame { background-color: #E6F3FF; border-radius: 6px; border: 1px solid #Cce5ff; } QLabel { color: #004085; font-size: 9pt; }")
        info_layout = QHBoxLayout(info_frame);
        info_layout.setContentsMargins(10, 8, 10, 8)
        lbl_info_icon = QLabel("💡");
        lbl_info_text = QLabel("提示：双击列表项可修改推荐程序；灰色状态表示该快捷方式已存在。")
        info_layout.addWidget(lbl_info_icon);
        info_layout.addWidget(lbl_info_text);
        info_layout.addStretch()
        layout.addWidget(info_frame)

        header_frame = QHBoxLayout()
        self.chk_select_all = QCheckBox("全选列表")
        self.chk_select_all.stateChanged.connect(self.toggle_select_all)
        self.lbl_count = QLabel("已选 0 / 共 0 个");
        self.lbl_count.setStyleSheet("font-weight: bold; color: #0078D7;")
        header_frame.addWidget(self.chk_select_all);
        header_frame.addStretch();
        header_frame.addWidget(self.lbl_count)
        layout.addLayout(header_frame)

        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(['程序名称', '推荐执行文件', '来源', '状态', '所在目录'])
        self.tree.setAlternatingRowColors(True);
        self.tree.setIconSize(QSize(24, 24))
        self.tree.itemDoubleClicked.connect(self.open_refine)
        self.tree.itemChanged.connect(self.on_tree_item_changed)
        layout.addWidget(self.tree)

        footer_layout = QVBoxLayout();
        footer_layout.setSpacing(5)
        self.lbl_path_hint = QLabel("")
        self.lbl_path_hint.setAlignment(Qt.AlignmentFlag.AlignRight);
        self.lbl_path_hint.setStyleSheet("color: #999999; font-size: 9pt;")
        self.btn_gen = QPushButton("✨ 生成选中快捷方式");
        self.btn_gen.setObjectName("primaryButton")
        self.btn_gen.setMinimumHeight(40);
        self.btn_gen.setEnabled(False);
        self.btn_gen.clicked.connect(self.generate)
        footer_layout.addWidget(self.lbl_path_hint);
        footer_layout.addWidget(self.btn_gen)
        layout.addLayout(footer_layout)

        last = self.config.get('Settings', 'last_scan_path', fallback='')
        if last: self.path_edit.setText(last)

    # 【Beta 5.4】 增加智能识别状态显示
    def update_rules_summary(self):
        conf = backend.load_config();
        rules = conf['Rules']
        summary = []
        if rules.getboolean('enable_blacklist', True): summary.append("黑名单✅")
        if rules.getboolean('enable_ignored_dirs', True): summary.append("黑洞跳过✅")
        if rules.getboolean('enable_size_filter', False):
            summary.append(f"大小({rules.get('min_size_kb')}K-{rules.get('max_size_mb')}M)")

        exts = rules.get('target_extensions', '.exe')
        # 显示智能识别状态
        smart_on = rules.getboolean('enable_smart_root', True)
        mode_text = "智能识别" if smart_on else "平铺模式"

        summary.append(f"类型({exts}) [{mode_text}]")

        self.lbl_rules_summary.setText("当前规则: " + " | ".join(summary) if summary else "当前规则: 无限制")

    def toggle_custom_path(self, checked):
        self.path_box.setVisible(checked)

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
        total = self.tree.topLevelItemCount();
        checked = 0;
        root = self.tree.invisibleRootItem()
        for i in range(total):
            if root.child(i).checkState(0) == Qt.CheckState.Checked: checked += 1
        self.lbl_count.setText(f"已选 {checked} / 共 {total} 个")
        self.chk_select_all.blockSignals(True)
        if total > 0 and checked == total:
            self.chk_select_all.setCheckState(Qt.CheckState.Checked)
        elif checked == 0:
            self.chk_select_all.setCheckState(Qt.CheckState.Unchecked)
        else:
            self.chk_select_all.setCheckState(Qt.CheckState.PartiallyChecked)
        self.chk_select_all.blockSignals(False)

    def browse_scan_path(self):
        d = QFileDialog.getExistingDirectory(self, "选择目录", self.path_edit.text())
        if d: self.path_edit.setText(d)

    def toggle_scan(self):
        if self.scan_thread and self.scan_thread.isRunning():
            self.scan_worker.stop();
            self.btn_action.setText("正在停止...");
            self.btn_action.setEnabled(False);
            return

        sources = []
        if self.chk_start_menu.isChecked(): sources.append('start_menu')
        if self.chk_uwp.isChecked(): sources.append('uwp')
        custom_path = ""
        if self.chk_custom.isChecked():
            custom_path = self.path_edit.text()
            if not custom_path: QMessageBox.warning(self, "提示",
                                                    "请选择自定义目录，或取消勾选'自定义目录'选项。"); return
            sources.append('custom')
        if not sources: QMessageBox.warning(self, "提示", "请至少选择一种扫描范围。"); return

        self.update_rules_summary()
        self.btn_action.setText("🛑 停止扫描");
        self.btn_action.setObjectName("stopButton");
        self.btn_action.setStyle(self.style())
        self.btn_gen.setEnabled(False);
        self.tree.clear();
        self.sig_status.emit(f"正在扫描... {sources}")
        self.chk_select_all.setCheckState(Qt.CheckState.Checked);
        self.lbl_count.setText("扫描中...")

        self.scan_thread = QThread(self);
        self.scan_worker = ScanWorker(sources, custom_path)
        self.scan_worker.moveToThread(self.scan_thread)
        self.scan_worker.log.connect(self.sig_log);
        self.scan_worker.finished.connect(self.on_scan_done)
        self.scan_thread.started.connect(self.scan_worker.run);
        self.scan_worker.finished.connect(self.scan_thread.quit)
        self.scan_thread.finished.connect(self.cleanup_thread);
        self.scan_thread.start()

    @Slot(list)
    def on_scan_done(self, res):
        self.programs = res;
        self.populate_tree()
        self.sig_status.emit(f"就绪 - 共发现 {len(res)} 个程序")
        self.btn_action.setText("🚀 开始扫描");
        self.btn_action.setObjectName("primaryButton");
        self.btn_action.setStyle(self.style())
        self.btn_action.setEnabled(True);
        self.btn_gen.setEnabled(len(res) > 0);
        self.update_selection_count()

    @Slot()
    def cleanup_thread(self):
        if self.scan_thread: self.scan_thread.deleteLater()
        if self.scan_worker: self.scan_worker.deleteLater()
        self.scan_thread = None;
        self.scan_worker = None

    def populate_tree(self):
        self.tree.clear();
        self.tree.blockSignals(True);
        items = []
        conf = backend.load_config()
        out_path = conf.get('Settings', 'output_path', fallback='').strip()
        if not out_path: out_path = os.path.join(os.path.expanduser('~'), 'Desktop', backend.DEFAULT_OUTPUT_FOLDER_NAME)

        # 读取策略
        rules = conf['Rules']
        check_new = rules.getboolean('default_check_new', True)
        check_exist = rules.getboolean('default_check_existing', False)

        existing_shortcuts = {}
        if os.path.exists(out_path):
            raw_list = backend.scan_existing_shortcuts(out_path)
            for name, target in raw_list:
                norm_target = backend.normalize_path(target)
                existing_shortcuts[norm_target] = name

        for i, p in enumerate(self.programs):
            target = p['selected_exes'][0] if p['selected_exes'] else ""
            if p.get('type') == 'uwp':
                name_disp = "UWP 应用"; norm_target = target
            else:
                name_disp = os.path.basename(target) if target else "未选择"; norm_target = backend.normalize_path(
                    target)

            status_text = "🆕 新增";
            status_tooltip = "新发现的程序";
            status_color = "#2E8B57"
            check_state = Qt.CheckState.Checked if check_new else Qt.CheckState.Unchecked

            if norm_target in existing_shortcuts:
                status_text = "✅ 已存在";
                status_tooltip = f"快捷方式已存在";
                status_color = "#888888"
                check_state = Qt.CheckState.Checked if check_exist else Qt.CheckState.Unchecked

            source_map = {'start_menu': '开始菜单', 'uwp': '应用商店', 'custom': '自定义'}
            source_text = source_map.get(p.get('type', 'custom'), '未知')

            item = QTreeWidgetItem([p['name'], name_disp, source_text, status_text, p['root_path']])
            item.setCheckState(0, check_state);
            item.setToolTip(4, p['root_path'])
            item.setForeground(3, QBrush(QColor(status_color)));
            item.setToolTip(3, status_tooltip)
            item.setTextAlignment(3, Qt.AlignmentFlag.AlignCenter)
            item.setForeground(2, QBrush(QColor("#005FB8")))

            if p.get('type') != 'uwp' and target:
                item.setIcon(1, self.icon_provider.icon(QFileInfo(target)));
                item.setToolTip(1, target)

            item.setData(0, Qt.ItemDataRole.UserRole, i)
            items.append(item)

        self.tree.addTopLevelItems(items)
        self.tree.header().resizeSections(QHeaderView.ResizeMode.ResizeToContents)
        self.tree.blockSignals(False)

    def open_refine(self, item):
        idx = item.data(0, Qt.ItemDataRole.UserRole);
        prog = self.programs[idx]
        if prog.get('type') == 'uwp' or prog.get('type') == 'start_menu': QMessageBox.information(self, "提示",
                                                                                                  "系统应用或开始菜单项不支持修改执行文件。"); return
        if RefineWindow(self, prog).exec() == QDialog.DialogCode.Accepted:
            target = prog['selected_exes'][0] if prog['selected_exes'] else ""
            item.setText(1, os.path.basename(target))
            if target: item.setIcon(1, self.icon_provider.icon(QFileInfo(target)))

    def generate(self):
        conf = backend.load_config()
        out = conf.get('Settings', 'output_path', fallback='').strip()
        if not out: out = os.path.join(os.path.expanduser('~'), 'Desktop', backend.DEFAULT_OUTPUT_FOLDER_NAME)
        if not os.path.exists(out): os.makedirs(out)
        tasks = []
        root = self.tree.invisibleRootItem()
        for i in range(root.childCount()):
            item = root.child(i)
            if item.checkState(0) == Qt.CheckState.Checked:
                idx = item.data(0, Qt.ItemDataRole.UserRole);
                p = self.programs[idx]
                for exe in p['selected_exes']:
                    name = os.path.splitext(os.path.basename(exe))[0]
                    if p.get('type') == 'uwp': name = p['name']
                    lnk_path = os.path.join(out, f"{name}.lnk")
                    args = f"shell:AppsFolder\\{exe}" if p.get('type') == 'uwp' else ""
                    tasks.append((exe, lnk_path, args))
        existing_files = set(os.listdir(out)) if os.path.exists(out) else set()
        overwrite_count = 0
        for _, lnk_path, _ in tasks:
            if os.path.basename(lnk_path) in existing_files: overwrite_count += 1
        if overwrite_count > 0:
            if QMessageBox.question(self, "覆盖确认", f"有 {overwrite_count} 个快捷方式冲突，是否覆盖？",
                                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No) == QMessageBox.StandardButton.No: return
        cnt = 0
        for exe, lnk_path, args in tasks:
            if backend.create_shortcut(exe, lnk_path, args)[0]: cnt += 1
        dialog = GenSuccessDialog(self, cnt, out);
        dialog.exec()

    def save_state(self):
        self.config['Settings']['last_scan_path'] = self.path_edit.text()
        backend.save_config(self.config)
        if self.scan_thread: self.scan_worker.stop(); self.scan_thread.wait(1000)