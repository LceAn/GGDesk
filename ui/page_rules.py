from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QTextEdit, QCheckBox, QGroupBox, QSpinBox, QDialog, QFrame, QMessageBox,
    QSlider
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QCursor
import scanner_backend as backend


# --- 阈值设置弹窗 ---
class DedupConfigDialog(QDialog):
    def __init__(self, parent, current_val):
        super().__init__(parent)
        self.setWindowTitle("去重灵敏度设置")
        self.resize(300, 150)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

        self.value = current_val

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("相似度判定阈值 (默认 60%)"))

        h = QHBoxLayout()
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(10, 100)
        self.slider.setValue(int(current_val * 100))
        self.lbl_val = QLabel(f"{int(current_val * 100)}%")

        self.slider.valueChanged.connect(lambda v: self.lbl_val.setText(f"{v}%"))
        h.addWidget(self.slider);
        h.addWidget(self.lbl_val)
        layout.addLayout(h)

        layout.addWidget(QLabel("值越低，判定越宽松（更多相似项会被识别）；\n值越高，判定越严格。"))

        btn = QPushButton("确定");
        btn.clicked.connect(self.accept)
        layout.addWidget(btn)

    def get_value(self):
        return self.slider.value() / 100.0


# ... (ListEditDialog 保持不变，省略) ...
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


# --- RulesPage ---
class RulesPage(QWidget):
    # ... (大部分代码保持不变，只修改 build_ui 中的 g_adv 部分) ...
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

        # 1. 目标文件
        g_ext = QGroupBox("目标文件与策略")
        l_ext = QVBoxLayout(g_ext);
        l_ext.setSpacing(10)
        row_exe = QHBoxLayout()
        self.chk_exe = QCheckBox("*.exe");
        self.chk_exe.setChecked(True);
        self.chk_exe.setEnabled(False)
        line_v = QFrame();
        line_v.setFrameShape(QFrame.Shape.VLine);
        line_v.setFrameShadow(QFrame.Shadow.Sunken)
        self.chk_smart = QCheckBox("启用智能根目录识别")
        self.btn_smart_help = QPushButton("❓");
        self.btn_smart_help.setFixedSize(20, 20);
        self.btn_smart_help.clicked.connect(self.show_smart_help)
        row_exe.addWidget(self.chk_exe);
        row_exe.addWidget(line_v);
        row_exe.addWidget(self.chk_smart);
        row_exe.addWidget(self.btn_smart_help);
        row_exe.addStretch();
        l_ext.addLayout(row_exe)
        row_other = QHBoxLayout()
        self.chk_jar = QCheckBox("*.jar");
        self.chk_bat = QCheckBox("*.bat / *.cmd");
        self.chk_lnk = QCheckBox("*.lnk")
        row_other.addWidget(self.chk_jar);
        row_other.addWidget(self.chk_bat);
        row_other.addWidget(self.chk_lnk);
        row_other.addStretch();
        l_ext.addLayout(row_other)
        layout.addWidget(g_ext)

        # 2. 过滤
        g_filter = QGroupBox("过滤规则")
        l_filter = QVBoxLayout(g_filter);
        l_filter.setSpacing(15)
        row_size = QHBoxLayout()
        self.chk_size = QCheckBox("启用大小过滤");
        self.chk_size.toggled.connect(self.toggle_size_inputs);
        row_size.addWidget(self.chk_size)
        row_size.addWidget(QLabel("  Min:"));
        self.spin_min = QSpinBox();
        self.spin_min.setSuffix(" KB");
        self.spin_min.setRange(0, 99999);
        row_size.addWidget(self.spin_min)
        row_size.addWidget(QLabel("  Max:"));
        self.spin_max = QSpinBox();
        self.spin_max.setSuffix(" MB");
        self.spin_max.setRange(1, 99999);
        row_size.addWidget(self.spin_max);
        row_size.addStretch();
        l_filter.addLayout(row_size)
        line2 = QFrame();
        line2.setFrameShape(QFrame.Shape.HLine);
        line2.setFrameShadow(QFrame.Shadow.Sunken);
        l_filter.addWidget(line2)
        row_blk = QHBoxLayout();
        self.chk_blk = QCheckBox("启用黑名单");
        btn_blk = QPushButton("📄 编辑黑名单");
        btn_blk.clicked.connect(self.edit_blacklist);
        row_blk.addWidget(self.chk_blk);
        row_blk.addWidget(btn_blk);
        row_blk.addStretch();
        l_filter.addLayout(row_blk)
        row_ign = QHBoxLayout();
        self.chk_ign = QCheckBox("启用目录跳过");
        btn_ign = QPushButton("📂 编辑黑洞目录");
        btn_ign.clicked.connect(self.edit_ignored);
        row_ign.addWidget(self.chk_ign);
        row_ign.addWidget(btn_ign);
        row_ign.addStretch();
        l_filter.addLayout(row_ign)
        layout.addWidget(g_filter)

        # 3. 高级策略 (【Beta 8.2 修改】)
        g_adv = QGroupBox("高级行为 (Behavior)")
        l_adv = QVBoxLayout(g_adv)

        h_dedup = QHBoxLayout()
        self.chk_dedup = QCheckBox("智能去重 (自动合并同名结果)")
        self.btn_dedup_conf = QPushButton("⚙️ 灵敏度")
        self.btn_dedup_conf.setFixedSize(80, 24)
        self.btn_dedup_conf.clicked.connect(self.config_dedup)
        h_dedup.addWidget(self.chk_dedup);
        h_dedup.addWidget(self.btn_dedup_conf);
        h_dedup.addStretch()
        l_adv.addLayout(h_dedup)

        l_adv.addWidget(QLabel("默认勾选:"))
        h_def = QHBoxLayout()
        self.chk_def_new = QCheckBox("🆕 新增");
        self.chk_def_exi = QCheckBox("✅ 已存在")
        h_def.addWidget(self.chk_def_new);
        h_def.addWidget(self.chk_def_exi);
        h_def.addStretch()
        l_adv.addLayout(h_def)
        layout.addWidget(g_adv)

        layout.addStretch()
        btn_save = QPushButton("💾 保存所有配置");
        btn_save.setObjectName("primaryButton");
        btn_save.clicked.connect(self.save_config)
        layout.addWidget(btn_save, 0, Qt.AlignmentFlag.AlignRight)

    # ... (辅助函数) ...
    def toggle_size_inputs(self, c):
        self.spin_min.setEnabled(c); self.spin_max.setEnabled(c)

    def show_smart_help(self):
        QMessageBox.information(self, "说明", "智能识别目录...")

    def edit_blacklist(self):
        d = ListEditDialog(self, "黑名单", self.blocklist, "一行一个:");
        if d.exec(): self.blocklist = d.get_data(); backend.save_blocklist(self.blocklist)

    def edit_ignored(self):
        d = ListEditDialog(self, "黑洞目录", self.ignored_dirs, "一行一个:");
        if d.exec(): self.ignored_dirs = d.get_data(); backend.save_ignored_dirs(self.ignored_dirs)

    # 【Beta 8.2】 配置灵敏度
    def config_dedup(self):
        cur = self.config['Rules'].getfloat('dedup_threshold', 0.6)
        d = DedupConfigDialog(self, cur)
        if d.exec():
            self.config['Rules']['dedup_threshold'] = str(d.get_value())

    def load_ui_states(self):
        r = self.config['Rules']
        self.chk_blk.setChecked(r.getboolean('enable_blacklist', True))
        self.chk_ign.setChecked(r.getboolean('enable_ignored_dirs', True))
        self.chk_size.setChecked(r.getboolean('enable_size_filter', False))
        self.spin_min.setValue(r.getint('min_size_kb', 0));
        self.spin_max.setValue(r.getint('max_size_mb', 500))

        self.chk_dedup.setChecked(r.getboolean('enable_deduplication', True))
        self.chk_def_new.setChecked(r.getboolean('default_check_new', True))
        self.chk_def_exi.setChecked(r.getboolean('default_check_existing', False))

        exts = r.get('target_extensions', '.exe')
        self.chk_exe.setChecked('.exe' in exts);
        self.chk_jar.setChecked('.jar' in exts)
        self.chk_bat.setChecked('.bat' in exts or '.cmd' in exts);
        self.chk_lnk.setChecked('.lnk' in exts)
        self.chk_smart.setChecked(r.getboolean('enable_smart_root', True))

    def save_config(self):
        r = self.config['Rules']
        r['enable_blacklist'] = str(self.chk_blk.isChecked())
        r['enable_ignored_dirs'] = str(self.chk_ign.isChecked())
        r['enable_size_filter'] = str(self.chk_size.isChecked())
        r['min_size_kb'] = str(self.spin_min.value());
        r['max_size_mb'] = str(self.spin_max.value())
        r['enable_deduplication'] = str(self.chk_dedup.isChecked())
        r['default_check_new'] = str(self.chk_def_new.isChecked())
        r['default_check_existing'] = str(self.chk_def_exi.isChecked())
        r['enable_smart_root'] = str(self.chk_smart.isChecked())

        exts = []
        if self.chk_exe.isChecked(): exts.append('.exe')
        if self.chk_jar.isChecked(): exts.append('.jar')
        if self.chk_bat.isChecked(): exts.extend(['.bat', '.cmd'])
        if self.chk_lnk.isChecked(): exts.append('.lnk')
        r['target_extensions'] = ",".join(exts)

        backend.save_config(self.config)
        QMessageBox.information(self, "完成", "规则配置已保存。")