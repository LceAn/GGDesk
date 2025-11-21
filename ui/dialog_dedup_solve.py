from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QTreeWidget, QTreeWidgetItem,
    QPushButton, QHBoxLayout, QHeaderView, QFrame, QMessageBox
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QBrush, QColor


class DeduplicateSolverDialog(QDialog):
    def __init__(self, parent, fuzzy_groups):
        super().__init__(parent)
        self.setWindowTitle("冲突确认 (Duplicate Resolver)")
        self.resize(800, 600)
        self.fuzzy_groups = fuzzy_groups  # [[item1, item2], [item3, item4]]
        self.resolved_items = []  # 用户决定保留的项

        self.build_ui()
        self.populate_tree()

    def build_ui(self):
        layout = QVBoxLayout(self);
        layout.setContentsMargins(20, 20, 20, 20);
        layout.setSpacing(15)

        # 提示头
        header = QLabel("⚠️ 发现疑似重复的程序")
        header.setStyleSheet("font-size: 14pt; font-weight: bold; color: #D94430;")
        layout.addWidget(header)

        desc = QLabel("以下程序名称或路径高度相似。请勾选您希望<b>保留</b>的项目。\n(未勾选的项目将不会显示在最终结果中)")
        desc.setStyleSheet("color: #666; margin-bottom: 10px;")
        layout.addWidget(desc)

        # 列表
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(['保留', '程序名称', '相似度来源', '完整路径'])
        self.tree.header().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.tree.header().setSectionResizeMode(3, QHeaderView.Stretch)
        self.tree.setAlternatingRowColors(True)
        layout.addWidget(self.tree)

        # 底部
        btn_box = QHBoxLayout()
        btn_all = QPushButton("全部保留 (不推荐)");
        btn_all.clicked.connect(self.check_all)
        btn_smart = QPushButton("智能选择 (推荐)");
        btn_smart.clicked.connect(self.smart_select)
        btn_smart.setToolTip("每组只保留路径最短或主要的一个")

        btn_ok = QPushButton("确认选择");
        btn_ok.setObjectName("primaryButton")
        btn_ok.clicked.connect(self.accept)

        btn_box.addWidget(btn_all);
        btn_box.addWidget(btn_smart)
        btn_box.addStretch();
        btn_box.addWidget(btn_ok)
        layout.addLayout(btn_box)

    def populate_tree(self):
        self.tree.clear()

        for group_idx, group in enumerate(self.fuzzy_groups):
            # 创建组头
            group_root = QTreeWidgetItem(self.tree)
            group_root.setText(0, f"冲突组 #{group_idx + 1}")
            group_root.setExpanded(True)
            group_root.setBackground(0, QBrush(QColor("#F0F0F0")))
            group_root.setFirstColumnSpanned(True)

            for item_data in group:
                item = QTreeWidgetItem(group_root)
                item.setCheckState(0, Qt.Unchecked)  # 默认不勾选
                item.setText(1, item_data['name'])
                item.setText(2, item_data.get('type', 'custom'))  # 来源
                item.setText(3, item_data.get('root_path', ''))
                item.setToolTip(3, item_data.get('root_path', ''))

                # 存储原始数据
                item.setData(0, Qt.UserRole, item_data)

        self.smart_select()  # 默认执行一次智能选择

    def smart_select(self):
        """策略：每组默认勾选第一个（通常是算法排序后的高分项），或者路径最短的"""
        root = self.tree.invisibleRootItem()
        for i in range(root.childCount()):
            group_item = root.child(i)

            # 找到该组内路径最短的作为推荐
            best_child = None
            min_len = 999999

            for j in range(group_item.childCount()):
                child = group_item.child(j)
                child.setCheckState(0, Qt.Unchecked)  # 先全取消

                path_len = len(child.text(3))
                if path_len < min_len:
                    min_len = path_len
                    best_child = child

            if best_child:
                best_child.setCheckState(0, Qt.Checked)

    def check_all(self):
        root = self.tree.invisibleRootItem()
        for i in range(root.childCount()):
            group_item = root.child(i)
            for j in range(group_item.childCount()):
                group_item.child(j).setCheckState(0, Qt.Checked)

    def get_selected_items(self):
        selected = []
        root = self.tree.invisibleRootItem()
        for i in range(root.childCount()):
            group_item = root.child(i)
            for j in range(group_item.childCount()):
                child = group_item.child(j)
                if child.checkState(0) == Qt.Checked:
                    selected.append(child.data(0, Qt.UserRole))
        return selected