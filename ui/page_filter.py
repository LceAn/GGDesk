from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QTextEdit, QSplitter, QMessageBox
)
from PySide6.QtCore import Qt
import scanner_backend as backend


class FilterPage(QWidget):
    def __init__(self):
        super().__init__()
        self.blocklist, _ = backend.load_blocklist()
        self.ignored_dirs, _ = backend.load_ignored_dirs()
        self.build_ui()

    def build_ui(self):
        layout = QVBoxLayout(self);
        layout.setContentsMargins(30, 30, 30, 30);
        layout.setSpacing(20)
        layout.addWidget(QLabel("🛡️ 过滤规则管理 (编辑后请保存)"), 0, Qt.AlignmentFlag.AlignBottom)
        splitter = QSplitter(Qt.Orientation.Horizontal)

        w1 = QWidget();
        l1 = QVBoxLayout(w1);
        l1.setContentsMargins(0, 0, 10, 0)
        l1.addWidget(QLabel("文件黑名单 (.exe)"));
        self.blk_edit = QTextEdit()
        self.blk_edit.setPlainText("\n".join(sorted(self.blocklist)));
        l1.addWidget(self.blk_edit);
        splitter.addWidget(w1)

        w2 = QWidget();
        l2 = QVBoxLayout(w2);
        l2.setContentsMargins(10, 0, 0, 0)
        l2.addWidget(QLabel("黑洞目录 (Dir)"));
        self.ign_edit = QTextEdit()
        self.ign_edit.setPlainText("\n".join(sorted(self.ignored_dirs)));
        l2.addWidget(self.ign_edit);
        splitter.addWidget(w2)

        layout.addWidget(splitter, 1)
        btn_save = QPushButton("💾 保存所有规则");
        btn_save.setObjectName("primaryButton");
        btn_save.clicked.connect(self.save_rules)
        layout.addWidget(btn_save, 0, Qt.AlignmentFlag.AlignRight)

    def save_rules(self):
        blk = {l.strip().lower() for l in self.blk_edit.toPlainText().split('\n') if l.strip()}
        ign = {l.strip() for l in self.ign_edit.toPlainText().split('\n') if l.strip()}
        backend.save_blocklist(blk);
        backend.save_ignored_dirs(ign)
        QMessageBox.information(self, "成功", "所有过滤规则已保存。")