from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QTextEdit, QCheckBox, QGroupBox, QSpinBox, QFrame, QMessageBox
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
        layout.addWidget(QLabel(help_text))
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
        self.resize(700, 600)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

        self.config = backend.load_config()
        self.blocklist, _ = backend.load_blocklist()
        self.ignored_dirs, _ = backend.load_ignored_dirs()

        self.build_ui()
        self.load_ui_states()

    def build_ui(self):
        layout = QVBoxLayout(self);
        layout.setContentsMargins(20, 20, 20, 20);
        layout.setSpacing(15)

        # 1. 目标文件 (Target)
        g_target = QGroupBox("目标文件类型 (Target Extensions)")
        l_target = QHBoxLayout(g_target)
        self.chk_exe = QCheckBox("*.exe");
        self.chk_exe.setChecked(True)
        self.chk_jar = QCheckBox("*.jar");
        self.chk_bat = QCheckBox("*.bat / *.cmd");
        self.chk_lnk = QCheckBox("*.lnk")
        l_target.addWidget(self.chk_exe);
        l_target.addWidget(self.chk_jar);
        l_target.addWidget(self.chk_bat);
        l_target.addWidget(self.chk_lnk)
        l_target.addStretch()
        layout.addWidget(g_target)

        # 2. 过滤规则 (Filters)
        g_filter = QGroupBox("过滤规则 (Filters)")
        l_filter = QVBoxLayout(g_filter);
        l_filter.setSpacing(10)

        # Size
        row_size = QHBoxLayout()
        self.chk_size = QCheckBox("启用大小过滤")
        self.chk_size.toggled.connect(lambda c: [self.spin_min.setEnabled(c), self.spin_max.setEnabled(c)])
        row_size.addWidget(self.chk_size)
        self.spin_min = QSpinBox();
        self.spin_min.setSuffix(" KB");
        self.spin_min.setRange(0, 999999)
        self.spin_max = QSpinBox();
        self.spin_max.setSuffix(" MB");
        self.spin_max.setRange(1, 999999)
        row_size.addWidget(QLabel(" Min:"));
        row_size.addWidget(self.spin_min)
        row_size.addWidget(QLabel(" Max:"));
        row_size.addWidget(self.spin_max);
        row_size.addStretch()
        l_filter.addLayout(row_size)

        # Lists
        row_lists = QHBoxLayout()
        self.chk_blk = QCheckBox("启用黑名单")
        btn_blk = QPushButton("编辑黑名单");
        btn_blk.clicked.connect(self.edit_blacklist)
        self.chk_ign = QCheckBox("启用黑洞目录")
        btn_ign = QPushButton("编辑黑洞目录");
        btn_ign.clicked.connect(self.edit_ignored)

        row_lists.addWidget(self.chk_blk);
        row_lists.addWidget(btn_blk);
        row_lists.addSpacing(20)
        row_lists.addWidget(self.chk_ign);
        row_lists.addWidget(btn_ign);
        row_lists.addStretch()
        l_filter.addLayout(row_lists)
        layout.addWidget(g_filter)

        # 3. 高级策略 (Strategy)
        g_adv = QGroupBox("高级策略 (Strategy)")
        l_adv = QVBoxLayout(g_adv)

        # 智能识别
        h_smart = QHBoxLayout()
        self.chk_smart = QCheckBox("启用智能根目录识别 (Smart Root)")
        btn_help = QPushButton("❓");
        btn_help.setFixedSize(20, 20);
        btn_help.setCursor(Qt.PointingHandCursor);
        btn_help.clicked.connect(self.show_smart_help)
        h_smart.addWidget(self.chk_smart);
        h_smart.addWidget(btn_help);
        h_smart.addStretch()
        l_adv.addLayout(h_smart)

        # 【Beta 9.1 修改】 去重策略配置归一化
        h_dedup = QHBoxLayout()
        # 更名：更直观
        self.chk_dedup = QCheckBox("扫描时自动忽略重复项 (Auto-Ignore Duplicates)")
        self.chk_dedup.setToolTip(
            "如果开启，扫描过程中发现同名程序时，将自动保留优先级更高的结果（自定义目录 > UWP > 开始菜单）。")

        # 只读显示当前阈值
        threshold = self.config['Rules'].getfloat('dedup_threshold', 0.6)
        self.lbl_dedup_val = QLabel(f"(当前全局判定阈值: {int(threshold * 100)}% - 请在[清理去重]工具中修改)")
        self.lbl_dedup_val.setStyleSheet("color: #888; font-style: italic; margin-left: 10px;")

        h_dedup.addWidget(self.chk_dedup);
        h_dedup.addWidget(self.lbl_dedup_val);
        h_dedup.addStretch()
        l_adv.addLayout(h_dedup)

        # 默认勾选
        l_adv.addWidget(QLabel("扫描结果默认勾选:"))
        h_def = QHBoxLayout()
        self.chk_def_new = QCheckBox("🆕 新增程序");
        self.chk_def_exi = QCheckBox("✅ 已存在程序")
        h_def.addWidget(self.chk_def_new);
        h_def.addWidget(self.chk_def_exi);
        h_def.addStretch()
        l_adv.addLayout(h_def)

        layout.addWidget(g_adv)

        # 底部按钮
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
        QMessageBox.information(self, "说明",
                                "<b>智能根目录识别:</b><br>"
                                "开启时：自动识别软件目录，评分选出最佳 EXE。<br>"
                                "关闭时：平铺列出所有 EXE。")

    def load_ui_states(self):
        r = self.config['Rules']
        exts = r.get('target_extensions', '.exe')
        self.chk_exe.setChecked('.exe' in exts)
        self.chk_jar.setChecked('.jar' in exts)
        self.chk_bat.setChecked('.bat' in exts or '.cmd' in exts)
        self.chk_lnk.setChecked('.lnk' in exts)

        self.chk_size.setChecked(r.getboolean('enable_size_filter', False))
        self.spin_min.setValue(r.getint('min_size_kb', 0));
        self.spin_max.setValue(r.getint('max_size_mb', 500))

        self.chk_blk.setChecked(r.getboolean('enable_blacklist', True))
        self.chk_ign.setChecked(r.getboolean('enable_ignored_dirs', True))

        self.chk_smart.setChecked(r.getboolean('enable_smart_root', True))
        self.chk_dedup.setChecked(r.getboolean('enable_deduplication', True))
        self.chk_def_new.setChecked(r.getboolean('default_check_new', True))
        self.chk_def_exi.setChecked(r.getboolean('default_check_existing', False))

    def edit_blacklist(self):
        d = ListEditDialog(self, "黑名单", self.blocklist, "一行一个:");
        if d.exec(): self.blocklist = d.get_data(); backend.save_blocklist(self.blocklist)

    def edit_ignored(self):
        d = ListEditDialog(self, "黑洞目录", self.ignored_dirs, "一行一个:");
        if d.exec(): self.ignored_dirs = d.get_data(); backend.save_ignored_dirs(self.ignored_dirs)

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
        r['enable_blacklist'] = str(self.chk_blk.isChecked());
        r['enable_ignored_dirs'] = str(self.chk_ign.isChecked())
        r['enable_smart_root'] = str(self.chk_smart.isChecked());
        r['enable_deduplication'] = str(self.chk_dedup.isChecked())
        r['default_check_new'] = str(self.chk_def_new.isChecked());
        r['default_check_existing'] = str(self.chk_def_exi.isChecked())

        backend.save_config(self.config)
        self.accept()