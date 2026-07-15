from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QTextEdit, QCheckBox, QGroupBox, QSpinBox, QFrame, QMessageBox,
    QGridLayout
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QCursor
import scanner_backend as backend


class ListEditDialog(QDialog):
    def __init__(self, parent, title, data_set, help_text):
        super().__init__(parent)
        self.setWindowTitle(title);
        self.resize(500, 400)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        layout = QVBoxLayout(self);
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(14)
        help_label = QLabel(help_text)
        help_label.setObjectName("captionLabel")
        layout.addWidget(help_label)
        self.editor = QTextEdit();
        self.editor.setPlainText("\n".join(sorted(data_set)));
        layout.addWidget(self.editor)
        btn_box = QHBoxLayout()
        btn_save = QPushButton("保存并关闭");
        btn_save.setObjectName("primaryButton");
        btn_save.clicked.connect(self.accept)
        btn_cancel = QPushButton("取消");
        btn_cancel.clicked.connect(self.reject)
        btn_box.addStretch();
        btn_box.addWidget(btn_save);
        btn_box.addWidget(btn_cancel);
        layout.addLayout(btn_box)

    def get_data(self): return {line.strip() for line in self.editor.toPlainText().split('\n') if line.strip()}


class RulesDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("扫描规则配置 (Scanner Rules)")
        self.resize(750, 600)  # 高度减小，因为少了一栏
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

        self.config = backend.load_config()
        self.blocklist, _ = backend.load_blocklist()
        self.ignored_dirs, _ = backend.load_ignored_dirs()
        self.prog_runtimes, _ = backend.manager_rules.load_prog_runtimes()
        self.bad_path_kws, _ = backend.manager_rules.load_bad_path_keywords()

        self.build_ui()
        self.load_ui_states()

    def build_ui(self):
        layout = QVBoxLayout(self);
        layout.setContentsMargins(24, 24, 24, 24);
        layout.setSpacing(18)
        title = QLabel("🛡️ 扫描器核心规则配置")
        title.setObjectName("pageTitle")
        layout.addWidget(title, 0, Qt.AlignmentFlag.AlignBottom)

        # 1. Target
        g_target = QGroupBox("1. 目标文件类型 (Target Extensions)")
        l_target = QHBoxLayout(g_target)
        self.chk_exe = QCheckBox("*.exe (可执行程序)");
        self.chk_exe.setChecked(True)
        self.chk_jar = QCheckBox("*.jar (Java 应用)");
        self.chk_bat = QCheckBox("*.bat / *.cmd (脚本)");
        self.chk_lnk = QCheckBox("*.lnk (快捷方式)")

        l_target.addWidget(self.chk_exe);
        l_target.addWidget(self.chk_jar);
        l_target.addWidget(self.chk_bat);
        l_target.addWidget(self.chk_lnk);
        l_target.addStretch()
        layout.addWidget(g_target)

        # 2. Filtering
        g_filter = QGroupBox("2. 过滤与清洗 (Filtering)")
        l_filter = QVBoxLayout(g_filter);
        l_filter.setSpacing(12)

        # 2.0 Size
        row_size = QHBoxLayout()
        self.chk_size = QCheckBox("启用文件大小过滤")
        self.chk_size.toggled.connect(lambda c: [self.spin_min.setEnabled(c), self.spin_max.setEnabled(c)])
        row_size.addWidget(self.chk_size)
        self.spin_min = QSpinBox();
        self.spin_min.setSuffix(" KB");
        self.spin_min.setRange(0, 999999)
        self.spin_min.setButtonSymbols(QSpinBox.ButtonSymbols.NoButtons)
        self.spin_max = QSpinBox();
        self.spin_max.setSuffix(" MB");
        self.spin_max.setRange(1, 999999)
        self.spin_max.setButtonSymbols(QSpinBox.ButtonSymbols.NoButtons)
        row_size.addWidget(QLabel(" Min:"));
        row_size.addWidget(self.spin_min)
        row_size.addWidget(QLabel(" Max:"));
        row_size.addWidget(self.spin_max);
        row_size.addStretch()
        l_filter.addLayout(row_size)

        # 2.1 Runtimes
        row_spec = QHBoxLayout()
        self.chk_prog = QCheckBox("🚫 过滤编程运行环境 (Python/Java/Node/Go...)")
        self.chk_prog.setToolTip("跳过解释器本身，只保留应用。")
        btn_prog = QPushButton("编辑列表");
        btn_prog.clicked.connect(self.edit_prog)
        row_spec.addWidget(self.chk_prog);
        row_spec.addStretch();
        row_spec.addWidget(btn_prog)
        l_filter.addLayout(row_spec)

        line = QFrame();
        line.setFrameShape(QFrame.Shape.HLine);
        line.setFrameShadow(QFrame.Shadow.Sunken);
        l_filter.addWidget(line)

        # 2.2 Blacklists
        def add_filter_row(chk_box, btn_text, slot_func):
            r = QHBoxLayout();
            r.addWidget(chk_box);
            r.addStretch()
            btn = QPushButton(btn_text);
            btn.setFixedWidth(100);
            btn.clicked.connect(slot_func)
            r.addWidget(btn);
            l_filter.addLayout(r)

        self.chk_blk = QCheckBox("🚫 过滤特定文件名 (Blacklist)")
        add_filter_row(self.chk_blk, "编辑列表", self.edit_blacklist)

        self.chk_ign = QCheckBox("📂 跳过指定目录 (Blackhole Dirs)")
        add_filter_row(self.chk_ign, "编辑列表", self.edit_ignored)

        self.chk_bad_path = QCheckBox("📂 跳过包含特定词的路径 (Bad Path)")
        add_filter_row(self.chk_bad_path, "编辑列表", self.edit_bad_path)

        layout.addWidget(g_filter)

        # 3. Strategy
        g_adv = QGroupBox("3. 智能策略 (Intelligence)")
        l_adv = QVBoxLayout(g_adv)

        h_smart = QHBoxLayout()
        self.chk_smart = QCheckBox("启用智能根目录识别 (Smart Root)")
        btn_help = QPushButton("❓");
        btn_help.setFixedSize(28, 28);
        btn_help.setObjectName("subtleButton")
        btn_help.setCursor(Qt.PointingHandCursor);
        btn_help.clicked.connect(self.show_smart_help)
        h_smart.addWidget(self.chk_smart);
        h_smart.addWidget(btn_help);
        h_smart.addStretch()
        l_adv.addLayout(h_smart)

        h_dedup = QHBoxLayout()
        self.chk_dedup = QCheckBox("扫描时自动忽略重复项 (Auto-Ignore)")
        threshold = self.config['Rules'].getfloat('dedup_threshold', 0.6)
        lbl_sens = QLabel(f"(当前全局灵敏度: {int(threshold * 100)}% - 在[清理去重]中修改)")
        lbl_sens.setObjectName("captionLabel")
        h_dedup.addWidget(self.chk_dedup);
        h_dedup.addWidget(lbl_sens);
        h_dedup.addStretch()
        l_adv.addLayout(h_dedup)
        layout.addWidget(g_adv)

        # Bot
        btn_box = QHBoxLayout();
        btn_box.addStretch()
        btn_save = QPushButton("保存并应用");
        btn_save.setObjectName("primaryButton");
        btn_save.setMinimumHeight(35);
        btn_save.clicked.connect(self.save_config)
        btn_cancel = QPushButton("取消");
        btn_cancel.setMinimumHeight(35);
        btn_cancel.clicked.connect(self.reject)
        btn_box.addWidget(btn_save);
        btn_box.addWidget(btn_cancel)
        layout.addLayout(btn_box)

    def show_smart_help(self):
        QMessageBox.information(self, "说明", "开启后：自动识别软件目录，评分选出最佳 EXE。\n关闭后：平铺列出所有 EXE。")

    def load_ui_states(self):
        r = self.config['Rules']
        exts = r.get('target_extensions', '.exe')
        self.chk_exe.setChecked('.exe' in exts);
        self.chk_jar.setChecked('.jar' in exts)
        self.chk_bat.setChecked('.bat' in exts or '.cmd' in exts);
        self.chk_lnk.setChecked('.lnk' in exts)

        self.chk_size.setChecked(r.getboolean('enable_size_filter', False))
        self.spin_min.setValue(r.getint('min_size_kb', 0));
        self.spin_max.setValue(r.getint('max_size_mb', 500))

        self.chk_blk.setChecked(r.getboolean('enable_blacklist', True))
        self.chk_ign.setChecked(r.getboolean('enable_ignored_dirs', True))
        self.chk_prog.setChecked(r.getboolean('enable_prog_filter', True))
        self.chk_bad_path.setChecked(r.getboolean('enable_bad_path', True))

        self.chk_smart.setChecked(r.getboolean('enable_smart_root', True))
        self.chk_dedup.setChecked(r.getboolean('enable_deduplication', True))

    def edit_blacklist(self):
        d = ListEditDialog(self, "编辑黑名单", self.blocklist, "文件名(一行一个):");
        if d.exec(): self.blocklist = d.get_data(); backend.save_blocklist(self.blocklist)

    def edit_ignored(self):
        d = ListEditDialog(self, "编辑黑洞目录", self.ignored_dirs, "目录名(一行一个):");
        if d.exec(): self.ignored_dirs = d.get_data(); backend.save_ignored_dirs(self.ignored_dirs)

    def edit_prog(self):
        d = ListEditDialog(self, "编辑运行环境名单", self.prog_runtimes, "文件名(一行一个):");
        if d.exec(): self.prog_runtimes = d.get_data(); backend.manager_rules.save_prog_runtimes(self.prog_runtimes)

    def edit_bad_path(self):
        d = ListEditDialog(self, "编辑路径关键词", self.bad_path_kws, "关键词(一行一个):");
        if d.exec(): self.bad_path_kws = d.get_data(); backend.manager_rules.save_bad_path_keywords(self.bad_path_kws)

    def save_config(self):
        r = self.config['Rules']
        exts = []
        if self.chk_exe.isChecked(): exts.append('.exe')
        if self.chk_jar.isChecked(): exts.append('.jar')
        if self.chk_bat.isChecked(): exts.extend(['.bat', '.cmd'])
        if self.chk_lnk.isChecked(): exts.append('.lnk')
        r['target_extensions'] = ",".join(exts)

        r['enable_size_filter'] = str(self.chk_size.isChecked())
        r['min_size_kb'] = str(self.spin_min.value());
        r['max_size_mb'] = str(self.spin_max.value())

        r['enable_blacklist'] = str(self.chk_blk.isChecked())
        r['enable_ignored_dirs'] = str(self.chk_ign.isChecked())
        r['enable_prog_filter'] = str(self.chk_prog.isChecked())
        r['enable_bad_path'] = str(self.chk_bad_path.isChecked())

        r['enable_smart_root'] = str(self.chk_smart.isChecked());
        r['enable_deduplication'] = str(self.chk_dedup.isChecked())

        backend.save_config(self.config)
        self.accept()
