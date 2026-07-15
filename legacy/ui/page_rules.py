from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QTreeWidget, QTreeWidgetItem, QHeaderView, QFrame, QMessageBox,
    QSlider, QGroupBox, QCheckBox, QFileIconProvider
)
from PySide6.QtCore import Qt, QSize, QFileInfo
from PySide6.QtGui import QIcon, QColor, QBrush, QAction
import os
import scanner_backend as backend
from scanner_backend.core_dedup import DuplicateAnalyzer


class DedupPage(QWidget):
    def __init__(self):
        super().__init__()
        self.config = backend.load_config()
        self.icon_provider = QFileIconProvider()
        self.build_ui()

    def build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 26, 28, 26)
        layout.setSpacing(18)

        title = QLabel("🧹 清理去重")
        title.setObjectName("pageTitle")
        layout.addWidget(title, 0, Qt.AlignmentFlag.AlignBottom)

        # --- 1. 头部控制区 (Analysis Strategy) ---
        top_box = QGroupBox("数据库深度清理 (Database Cleanup)")
        top_layout = QHBoxLayout(top_box)

        # 标签
        top_layout.addWidget(QLabel("相似度阈值 (Sensitivity):"))

        # 滑块
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(10, 100)

        # 读取全局配置作为默认值
        global_threshold = self.config['Rules'].getfloat('dedup_threshold', 0.6)
        self.slider.setValue(int(global_threshold * 100))

        # 数值显示
        self.lbl_val = QLabel(f"{int(global_threshold * 100)}%")
        self.slider.valueChanged.connect(lambda v: self.lbl_val.setText(f"{v}%"))

        # 【Beta 9.1】 保存为全局默认按钮
        btn_save_default = QPushButton("💾 设为全局默认")
        btn_save_default.setObjectName("subtleButton")
        btn_save_default.setToolTip("将当前滑块值保存为全局默认灵敏度，\n这也将影响[扫描程序]中的去重判断。")
        btn_save_default.clicked.connect(self.save_threshold_global)

        top_layout.addWidget(self.slider)
        top_layout.addWidget(self.lbl_val)
        top_layout.addWidget(btn_save_default)

        top_layout.addSpacing(20)

        # 扫描按钮
        self.btn_scan = QPushButton("🔍 扫描数据库重复项")
        self.btn_scan.setObjectName("primaryButton")
        self.btn_scan.setMinimumHeight(35)
        self.btn_scan.clicked.connect(self.start_analysis)
        top_layout.addWidget(self.btn_scan)

        layout.addWidget(top_box)

        # --- 2. 结果列表 (Results) ---
        info_layout = QHBoxLayout()
        info_layout.addWidget(QLabel("⚠️ 疑似重复组 (请勾选需要【删除】的项目)"))
        info_layout.addStretch()
        self.lbl_count = QLabel("未开始扫描")
        self.lbl_count.setObjectName("metricLabel")
        info_layout.addWidget(self.lbl_count)
        layout.addLayout(info_layout)

        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(['程序名称', 'ID', '完整路径', '来源'])
        self.tree.header().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.tree.header().setSectionResizeMode(2, QHeaderView.Stretch)
        self.tree.setAlternatingRowColors(True)
        layout.addWidget(self.tree)

        # --- 3. 底部操作 (Actions) ---
        bot_layout = QHBoxLayout()

        self.chk_del_file = QCheckBox("同时删除本地生成的 .lnk 文件")
        self.chk_del_file.setChecked(False)  # 默认只删数据库记录，安全第一

        self.btn_clean = QPushButton("🗑️ 清理选中项")
        self.btn_clean.setObjectName("dangerButton")
        self.btn_clean.setEnabled(False)
        self.btn_clean.clicked.connect(self.clean_selected)

        bot_layout.addWidget(self.chk_del_file)
        bot_layout.addStretch()
        bot_layout.addWidget(self.btn_clean)
        layout.addLayout(bot_layout)

    # 【Beta 9.1】 反向同步配置
    def save_threshold_global(self):
        val = str(self.slider.value() / 100.0)
        self.config['Rules']['dedup_threshold'] = val
        backend.save_config(self.config)
        QMessageBox.information(self, "已保存",
                                f"全局判重灵敏度已更新为 {self.lbl_val.text()}。\n扫描程序也将使用此标准。")

    def start_analysis(self):
        self.tree.clear()
        self.btn_clean.setEnabled(False)
        self.lbl_count.setText("分析中...")

        # 1. 获取数据库所有数据
        db_rows = backend.get_all_shortcuts()
        if not db_rows:
            QMessageBox.information(self, "提示", "数据库为空。")
            self.lbl_count.setText("无数据")
            return

        # 2. 转换为 Analyzer 需要的格式
        program_list = []
        for row in db_rows:
            p = {
                'name': row['name'],
                'root_path': os.path.dirname(row['exe_path']) if row['exe_path'] else "",
                'type': row['source_type'],
                'db_id': row['id'],
                'exe_path': row['exe_path'],
                'lnk_path': row['lnk_path']
            }
            program_list.append(p)

        # 3. 运行分析器
        threshold = self.slider.value() / 100.0
        analyzer = DuplicateAnalyzer(threshold)
        groups = self.run_clustering(program_list, analyzer)

        # 4. 渲染结果
        total_groups = 0
        for group in groups:
            if len(group) < 2: continue  # 只有一个的不算重复
            total_groups += 1

            # 创建组头
            root = QTreeWidgetItem(self.tree)
            root.setText(0, f"冲突组 #{total_groups} - {group[0]['name']} 等")
            root.setExpanded(True)
            root.setBackground(0, QBrush(QColor("#FFF8E1")))  # 淡黄背景
            root.setFirstColumnSpanned(True)

            for p in group:
                item = QTreeWidgetItem(root)
                item.setText(0, p['name'])
                item.setText(1, str(p['db_id']))
                item.setText(2, p['exe_path'])
                item.setText(3, p['type'])
                item.setToolTip(2, p['exe_path'])

                # 设置图标
                icon_path = p['lnk_path'] if os.path.exists(p['lnk_path']) else p['exe_path']
                if p['type'] != 'uwp':
                    item.setIcon(0, self.icon_provider.icon(QFileInfo(icon_path)))

                # 复选框：用于标记删除
                item.setCheckState(0, Qt.Unchecked)
                item.setData(0, Qt.UserRole, p)  # 存储完整数据

        self.lbl_count.setText(f"发现 {total_groups} 组相似项")
        if total_groups > 0:
            self.btn_clean.setEnabled(True)
        else:
            QMessageBox.information(self, "完美", "未发现明显的重复或相似项目。")

    def run_clustering(self, items, analyzer):
        """
        聚类逻辑：找出相似的组
        """
        clusters = []
        visited = set()

        # 按名称排序，加速邻近比较
        items.sort(key=lambda x: x['name'])

        for i in range(len(items)):
            if i in visited: continue

            current_cluster = [items[i]]
            visited.add(i)

            for j in range(i + 1, len(items)):
                if j in visited: continue

                # 使用 analyzer 的核心相似度算法
                if analyzer._is_similar(items[i], items[j]):
                    current_cluster.append(items[j])
                    visited.add(j)

            clusters.append(current_cluster)

        return clusters

    def clean_selected(self):
        selected_items = []

        # 遍历树寻找被勾选的子项
        root = self.tree.invisibleRootItem()
        for i in range(root.childCount()):
            group = root.child(i)
            for j in range(group.childCount()):
                child = group.child(j)
                if child.checkState(0) == Qt.Checked:
                    selected_items.append(child.data(0, Qt.UserRole))

        if not selected_items:
            QMessageBox.warning(self, "提示", "请先勾选要删除的项目。")
            return

        text = f"确定要删除这 {len(selected_items)} 个项目吗？"
        if self.chk_del_file.isChecked():
            text += "\n\n⚠️ 注意：关联的本地快捷方式文件 (.lnk) 也会被物理删除！"

        if QMessageBox.question(self, "确认清理", text, QMessageBox.Yes | QMessageBox.No) == QMessageBox.Yes:

            deleted_count = 0
            for p in selected_items:
                # 1. 删库
                backend.delete_shortcut(p['db_id'])

                # 2. 删文件 (如果勾选)
                if self.chk_del_file.isChecked() and p['lnk_path'] and os.path.exists(p['lnk_path']):
                    try:
                        os.remove(p['lnk_path'])
                    except Exception as e:
                        print(f"删除文件失败: {e}")

                deleted_count += 1

            QMessageBox.information(self, "成功", f"已清理 {deleted_count} 个项目。")
            self.start_analysis()  # 刷新列表
