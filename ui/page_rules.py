from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QTextEdit, QCheckBox, QGroupBox, QSpinBox, QRadioButton,
    QButtonGroup, QDialog, QFrame, QMessageBox
)
from PySide6.QtCore import Qt
import scanner_backend as backend


# --- 通用文本编辑弹窗 (保持不变) ---
class ListEditDialog(QDialog):
    def __init__(self, parent, title, data_set, help_text):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(500, 400)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(help_text))

        self.editor = QTextEdit()
        self.editor.setPlainText("\n".join(sorted(data_set)))
        layout.addWidget(self.editor)

        btn_box = QHBoxLayout()
        btn_save = QPushButton("保存并关闭")
        btn_save.setObjectName("primaryButton")
        btn_save.clicked.connect(self.accept)
        btn_cancel = QPushButton("取消")
        btn_cancel.clicked.connect(self.reject)
        btn_box.addStretch();
        btn_box.addWidget(btn_save);
        btn_box.addWidget(btn_cancel)
        layout.addLayout(btn_box)

    def get_data(self):
        text = self.editor.toPlainText()
        return {line.strip() for line in text.split('\n') if line.strip()}


class RulesPage(QWidget):
    def __init__(self):
        super().__init__()
        self.config = backend.load_config()
        # 加载列表数据
        self.blocklist, _ = backend.load_blocklist()
        self.ignored_dirs, _ = backend.load_ignored_dirs()
        self.build_ui()
        self.load_ui_states()

    def build_ui(self):
        layout = QVBoxLayout(self);
        layout.setContentsMargins(30, 30, 30, 30);
        layout.setSpacing(20)

        layout.addWidget(QLabel("🛡️ 扫描规则配置"), 0, Qt.AlignmentFlag.AlignBottom)

        # --- 【Beta 5.1.1 修正】 移除了“扫描范围”组，因为已移动至扫描首页 ---

        # --- 1. 文件类型 (原序号2) ---
        g_ext = QGroupBox("目标文件类型 (Target Extensions)")
        l_ext = QHBoxLayout(g_ext)

        self.chk_exe = QCheckBox("*.exe (可执行程序)")
        self.chk_exe.setChecked(True)  # 默认必须有
        self.chk_exe.setEnabled(False)  # 强制开启
        l_ext.addWidget(self.chk_exe)

        self.chk_bat = QCheckBox("*.bat / *.cmd (脚本)")
        self.chk_bat.setEnabled(False)  # 预留
        l_ext.addWidget(self.chk_bat)

        self.chk_lnk = QCheckBox("*.lnk (快捷方式)")
        self.chk_lnk.setEnabled(False)  # 预留
        l_ext.addWidget(self.chk_lnk)

        l_ext.addStretch()
        layout.addWidget(g_ext)

        # --- 2. 过滤规则 (原序号3) ---
        g_filter = QGroupBox("过滤规则 (Filter Rules)")
        l_filter = QVBoxLayout(g_filter);
        l_filter.setSpacing(15)

        # 2.1 大小过滤
        row_size = QHBoxLayout()
        self.chk_size = QCheckBox("启用文件大小过滤")
        self.chk_size.toggled.connect(self.toggle_size_inputs)
        row_size.addWidget(self.chk_size)

        row_size.addWidget(QLabel("  最小:"))
        self.spin_min = QSpinBox();
        self.spin_min.setSuffix(" KB");
        self.spin_min.setRange(0, 99999)
        row_size.addWidget(self.spin_min)

        row_size.addWidget(QLabel("  最大:"))
        self.spin_max = QSpinBox();
        self.spin_max.setSuffix(" MB");
        self.spin_max.setRange(1, 99999)
        row_size.addWidget(self.spin_max)

        row_size.addStretch()
        l_filter.addLayout(row_size)

        line = QFrame();
        line.setFrameShape(QFrame.Shape.HLine);
        line.setFrameShadow(QFrame.Shadow.Sunken);
        l_filter.addWidget(line)

        # 2.2 黑名单
        row_blk = QHBoxLayout()
        self.chk_blk = QCheckBox("启用文件名黑名单 (Blacklist)")
        row_blk.addWidget(self.chk_blk)
        btn_blk = QPushButton("📄 查看/编辑详情");
        btn_blk.clicked.connect(self.edit_blacklist)
        row_blk.addStretch();
        row_blk.addWidget(btn_blk)
        l_filter.addLayout(row_blk)

        # 2.3 黑洞目录
        row_ign = QHBoxLayout()
        self.chk_ign = QCheckBox("启用黑洞目录跳过 (Ignore Dirs)")
        row_ign.addWidget(self.chk_ign)
        btn_ign = QPushButton("📂 查看/编辑详情");
        btn_ign.clicked.connect(self.edit_ignored)
        row_ign.addStretch();
        row_ign.addWidget(btn_ign)
        l_filter.addLayout(row_ign)

        layout.addWidget(g_filter)

        # 保存按钮
        layout.addStretch()
        btn_save = QPushButton("💾 保存所有规则配置");
        btn_save.setObjectName("primaryButton")
        btn_save.clicked.connect(self.save_config)
        layout.addWidget(btn_save, 0, Qt.AlignmentFlag.AlignRight)

    def toggle_size_inputs(self, checked):
        self.spin_min.setEnabled(checked)
        self.spin_max.setEnabled(checked)

    def load_ui_states(self):
        rules = self.config['Rules']
        self.chk_blk.setChecked(rules.getboolean('enable_blacklist', True))
        self.chk_ign.setChecked(rules.getboolean('enable_ignored_dirs', True))

        size_on = rules.getboolean('enable_size_filter', False)
        self.chk_size.setChecked(size_on)
        self.toggle_size_inputs(size_on)

        self.spin_min.setValue(rules.getint('min_size_kb', 0))
        self.spin_max.setValue(rules.getint('max_size_mb', 500))

    def edit_blacklist(self):
        dlg = ListEditDialog(self, "编辑文件名黑名单", self.blocklist, "跳过包含以下关键词的文件 (不区分大小写):")
        if dlg.exec():
            self.blocklist = dlg.get_data()
            backend.save_blocklist(self.blocklist)

    def edit_ignored(self):
        dlg = ListEditDialog(self, "编辑黑洞目录", self.ignored_dirs, "完全跳过以下目录名称 (精确匹配):")
        if dlg.exec():
            self.ignored_dirs = dlg.get_data()
            backend.save_ignored_dirs(self.ignored_dirs)

    def save_config(self):
        rules = self.config['Rules']
        rules['enable_blacklist'] = str(self.chk_blk.isChecked())
        rules['enable_ignored_dirs'] = str(self.chk_ign.isChecked())
        rules['enable_size_filter'] = str(self.chk_size.isChecked())
        rules['min_size_kb'] = str(self.spin_min.value())
        rules['max_size_mb'] = str(self.spin_max.value())

        backend.save_config(self.config)
        QMessageBox.information(self, "完成", "规则配置已更新，将在下次扫描时生效。")