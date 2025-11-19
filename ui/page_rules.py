from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QTextEdit, QCheckBox, QGroupBox, QSpinBox, QRadioButton,
    QButtonGroup, QDialog, QFrame, QMessageBox
)
from PySide6.QtCore import Qt
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


class RulesPage(QWidget):
    def __init__(self):
        super().__init__()
        self.config = backend.load_config()
        self.blocklist, _ = backend.load_blocklist()
        self.ignored_dirs, _ = backend.load_ignored_dirs()
        self.build_ui()
        self.load_ui_states()

    def build_ui(self):
        layout = QVBoxLayout(self);
        layout.setContentsMargins(30, 30, 30, 30);
        layout.setSpacing(20)
        layout.addWidget(QLabel("🛡️ 扫描规则配置"), 0, Qt.AlignmentFlag.AlignBottom)

        # 1. 文件类型
        g_ext = QGroupBox("目标文件类型")
        l_ext = QHBoxLayout(g_ext)
        self.chk_exe = QCheckBox("*.exe");
        self.chk_exe.setChecked(True);
        self.chk_exe.setEnabled(False);
        l_ext.addWidget(self.chk_exe)
        self.chk_bat = QCheckBox("*.bat (Beta 6)");
        self.chk_bat.setEnabled(False);
        l_ext.addWidget(self.chk_bat)
        self.chk_lnk = QCheckBox("*.lnk (Beta 6)");
        self.chk_lnk.setEnabled(False);
        l_ext.addWidget(self.chk_lnk)
        l_ext.addStretch();
        layout.addWidget(g_ext)

        # 2. 过滤规则
        g_filter = QGroupBox("过滤规则")
        l_filter = QVBoxLayout(g_filter);
        l_filter.setSpacing(15)

        row_size = QHBoxLayout()
        self.chk_size = QCheckBox("启用大小过滤");
        self.chk_size.toggled.connect(self.toggle_size_inputs);
        row_size.addWidget(self.chk_size)
        row_size.addWidget(QLabel("  最小:"));
        self.spin_min = QSpinBox();
        self.spin_min.setSuffix(" KB");
        self.spin_min.setRange(0, 99999);
        row_size.addWidget(self.spin_min)
        row_size.addWidget(QLabel("  最大:"));
        self.spin_max = QSpinBox();
        self.spin_max.setSuffix(" MB");
        self.spin_max.setRange(1, 99999);
        row_size.addWidget(self.spin_max)
        row_size.addStretch();
        l_filter.addLayout(row_size)

        line = QFrame();
        line.setFrameShape(QFrame.Shape.HLine);
        line.setFrameShadow(QFrame.Shadow.Sunken);
        l_filter.addWidget(line)

        row_blk = QHBoxLayout();
        self.chk_blk = QCheckBox("启用黑名单");
        row_blk.addWidget(self.chk_blk)
        btn_blk = QPushButton("📄 编辑黑名单");
        btn_blk.clicked.connect(self.edit_blacklist);
        row_blk.addStretch();
        row_blk.addWidget(btn_blk);
        l_filter.addLayout(row_blk)

        row_ign = QHBoxLayout();
        self.chk_ign = QCheckBox("启用目录跳过");
        row_ign.addWidget(self.chk_ign)
        btn_ign = QPushButton("📂 编辑黑洞目录");
        btn_ign.clicked.connect(self.edit_ignored);
        row_ign.addStretch();
        row_ign.addWidget(btn_ign);
        l_filter.addLayout(row_ign)
        layout.addWidget(g_filter)

        # 3. 【Beta 5.3】 高级策略
        g_adv = QGroupBox("高级策略 (Behavior)")
        l_adv = QVBoxLayout(g_adv)

        self.chk_dedup = QCheckBox("智能去重：合并 StartMenu/UWP/Custom 中同名的程序")
        l_adv.addWidget(self.chk_dedup)

        l_adv.addWidget(QLabel("扫描结果默认勾选状态:"))
        h_def = QHBoxLayout()
        self.chk_def_new = QCheckBox("默认勾选 [🆕 新增] 程序")
        self.chk_def_exi = QCheckBox("默认勾选 [✅ 已存在] 程序")
        h_def.addWidget(self.chk_def_new);
        h_def.addWidget(self.chk_def_exi);
        h_def.addStretch()
        l_adv.addLayout(h_def)

        layout.addWidget(g_adv)

        # Save
        layout.addStretch()
        btn_save = QPushButton("💾 保存所有配置");
        btn_save.setObjectName("primaryButton");
        btn_save.clicked.connect(self.save_config)
        layout.addWidget(btn_save, 0, Qt.AlignmentFlag.AlignRight)

    def toggle_size_inputs(self, checked):
        self.spin_min.setEnabled(checked);
        self.spin_max.setEnabled(checked)

    def load_ui_states(self):
        rules = self.config['Rules']
        self.chk_blk.setChecked(rules.getboolean('enable_blacklist', True))
        self.chk_ign.setChecked(rules.getboolean('enable_ignored_dirs', True))
        size_on = rules.getboolean('enable_size_filter', False)
        self.chk_size.setChecked(size_on);
        self.toggle_size_inputs(size_on)
        self.spin_min.setValue(rules.getint('min_size_kb', 0))
        self.spin_max.setValue(rules.getint('max_size_mb', 500))

        # 【Beta 5.3】
        self.chk_dedup.setChecked(rules.getboolean('enable_deduplication', True))
        self.chk_def_new.setChecked(rules.getboolean('default_check_new', True))
        self.chk_def_exi.setChecked(rules.getboolean('default_check_existing', False))

    def edit_blacklist(self):
        dlg = ListEditDialog(self, "编辑文件名黑名单", self.blocklist, "每行一个关键词:")
        if dlg.exec(): self.blocklist = dlg.get_data(); backend.save_blocklist(self.blocklist)

    def edit_ignored(self):
        dlg = ListEditDialog(self, "编辑黑洞目录", self.ignored_dirs, "每行一个目录名:")
        if dlg.exec(): self.ignored_dirs = dlg.get_data(); backend.save_ignored_dirs(self.ignored_dirs)

    def save_config(self):
        rules = self.config['Rules']
        rules['enable_blacklist'] = str(self.chk_blk.isChecked())
        rules['enable_ignored_dirs'] = str(self.chk_ign.isChecked())
        rules['enable_size_filter'] = str(self.chk_size.isChecked())
        rules['min_size_kb'] = str(self.spin_min.value())
        rules['max_size_mb'] = str(self.spin_max.value())

        # 【Beta 5.3】
        rules['enable_deduplication'] = str(self.chk_dedup.isChecked())
        rules['default_check_new'] = str(self.chk_def_new.isChecked())
        rules['default_check_existing'] = str(self.chk_def_exi.isChecked())

        backend.save_config(self.config)
        QMessageBox.information(self, "完成", "配置已保存。")