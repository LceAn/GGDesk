from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLineEdit, QLabel,
    QTreeWidget, QTreeWidgetItem, QHeaderView, QFileDialog, QFrame,
    QFileIconProvider  # <--- 移到这里
)
from PySide6.QtCore import Qt, Signal, QFileInfo, QSize
# from PySide6.QtGui import QFileIconProvider  <--- 删除这行
import os
import scanner_backend as backend


class OutputPage(QWidget):
    sig_path_changed = Signal(str)

    def __init__(self):
        super().__init__()
        self.config = backend.load_config()
        self.icon_provider = QFileIconProvider()
        self.build_ui()

    def build_ui(self):
        layout = QVBoxLayout(self);
        layout.setContentsMargins(28, 26, 28, 26);
        layout.setSpacing(18)

        title = QLabel("💾 快捷方式生成路径设置")
        title.setObjectName("pageTitle")
        layout.addWidget(title, 0, Qt.AlignmentFlag.AlignBottom)
        path_box = QHBoxLayout()
        self.out_edit = QLineEdit();
        self.out_edit.setPlaceholderText("默认桌面")
        self.out_edit.textChanged.connect(self.on_path_changed)
        btn_out = QPushButton("浏览...");
        btn_out.setObjectName("subtleButton")
        btn_out.clicked.connect(self.browse_out_path)
        path_box.addWidget(self.out_edit);
        path_box.addWidget(btn_out);
        layout.addLayout(path_box)

        sep = QFrame();
        sep.setFrameShape(QFrame.Shape.HLine);
        sep.setFrameShadow(QFrame.Shadow.Sunken);
        layout.addWidget(sep)

        section = QLabel("📂 当前路径下已存在的快捷方式 (预览)")
        section.setObjectName("sectionLabel")
        layout.addWidget(section, 0, Qt.AlignmentFlag.AlignBottom)
        self.out_tree = QTreeWidget();
        self.out_tree.setHeaderLabels(['快捷方式名称', '指向目标'])
        self.out_tree.setAlternatingRowColors(True);
        self.out_tree.setIconSize(QSize(24, 24))
        layout.addWidget(self.out_tree)

        btn_refresh = QPushButton("刷新列表");
        btn_refresh.setObjectName("subtleButton")
        btn_refresh.clicked.connect(self.refresh_existing_shortcuts)
        layout.addWidget(btn_refresh, 0, Qt.AlignmentFlag.AlignRight)

        # Init
        self.out_edit.setText(self.config.get('Settings', 'output_path', fallback=''))

    def on_path_changed(self, text):
        self.refresh_existing_shortcuts()
        self.sig_path_changed.emit(text)

    def browse_out_path(self):
        d = QFileDialog.getExistingDirectory(self, "选择目录", self.out_edit.text())
        if d: self.out_edit.setText(d)

    def refresh_existing_shortcuts(self):
        path = self.out_edit.text()
        if not path: path = os.path.join(os.path.expanduser('~'), 'Desktop', backend.DEFAULT_OUTPUT_FOLDER_NAME)
        self.out_tree.clear()
        if os.path.exists(path):
            items = backend.scan_existing_shortcuts(path)
            for name, target in items:
                t = QTreeWidgetItem([name, target])
                full_lnk = os.path.join(path, name)
                t.setIcon(0, self.icon_provider.icon(QFileInfo(full_lnk)))
                self.out_tree.addTopLevelItem(t)
            self.out_tree.header().resizeSections(QHeaderView.ResizeMode.ResizeToContents)
        else:
            self.out_tree.addTopLevelItem(QTreeWidgetItem(["(目录不存在)", ""]))

    def save_state(self):
        self.config['Settings']['output_path'] = self.out_edit.text()
        backend.save_config(self.config)
