from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QTableWidget, QTableWidgetItem,
    QPushButton, QHBoxLayout, QHeaderView, QMessageBox, QAbstractItemView,
    QGroupBox, QSlider, QComboBox, QCheckBox, QDialog, QApplication, QStyle,
    QFileIconProvider  # <--- 【修复】 正确的位置在这里
)
from PySide6.QtCore import Qt, Signal, QFileInfo
# from PySide6.QtGui import QFileIconProvider <--- 【错误】 已移除
import os
import scanner_backend as backend


# --- 数据库弹窗 ---
class DatabaseDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("数据库高级管理")
        self.resize(800, 600)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self.icon_provider = QFileIconProvider()
        self.build_ui()
        self.load_data()

    def build_ui(self):
        layout = QVBoxLayout(self);
        layout.setContentsMargins(20, 20, 20, 20)
        self.table = QTableWidget();
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["ID", "名称", "类型", "路径", "次数"])
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows);
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setAlternatingRowColors(True);
        self.table.verticalHeader().setVisible(False)
        header = self.table.horizontalHeader();
        header.setSectionResizeMode(3, QHeaderView.Stretch)
        layout.addWidget(self.table)
        btn_box = QHBoxLayout()
        btn_del = QPushButton("删除选中");
        btn_del.clicked.connect(self.delete_selected)
        btn_close = QPushButton("关闭");
        btn_close.clicked.connect(self.accept)
        btn_box.addStretch();
        btn_box.addWidget(btn_del);
        btn_box.addWidget(btn_close);
        layout.addLayout(btn_box)

    def load_data(self):
        self.table.setRowCount(0)
        data = backend.get_all_shortcuts()
        self.table.setRowCount(len(data))
        for i, row in enumerate(data):
            self.table.setItem(i, 0, QTableWidgetItem(str(row['id'])))
            item_name = QTableWidgetItem(row['name'])
            path = row['lnk_path'] if os.path.exists(row['lnk_path']) else row['exe_path']
            if row['source_type'] != 'uwp': item_name.setIcon(self.icon_provider.icon(QFileInfo(path)))
            self.table.setItem(i, 1, item_name)
            self.table.setItem(i, 2, QTableWidgetItem(row['source_type']))
            self.table.setItem(i, 3, QTableWidgetItem(row['exe_path']))
            self.table.setItem(i, 4, QTableWidgetItem(str(row['run_count'])))

    def delete_selected(self):
        rows = sorted(set(i.row() for i in self.table.selectedItems()), reverse=True)
        if not rows: return
        if QMessageBox.question(self, "确认", f"删除 {len(rows)} 项?",
                                QMessageBox.Yes | QMessageBox.No) == QMessageBox.No: return
        for r in rows: backend.delete_shortcut(int(self.table.item(r, 0).text()))
        self.load_data()


# --- 管理主页 ---
class LaunchManagePage(QWidget):
    sig_settings_changed = Signal()

    def __init__(self):
        super().__init__()
        self.config = backend.load_config()
        self.build_ui()
        self.load_ui_states()

    def build_ui(self):
        layout = QVBoxLayout(self);
        layout.setContentsMargins(30, 30, 30, 30);
        layout.setSpacing(20)
        layout.addWidget(QLabel("🛠️ 启动器配置"), 0, Qt.AlignmentFlag.AlignBottom)

        g_view = QGroupBox("视图设置")
        l_view = QHBoxLayout(g_view)
        l_view.addWidget(QLabel("图标大小:"))
        self.slider_size = QSlider(Qt.Orientation.Horizontal);
        self.slider_size.setRange(48, 128);
        self.slider_size.setFixedWidth(150)
        self.slider_size.valueChanged.connect(self.save_settings)
        l_view.addWidget(self.slider_size);
        self.lbl_size_val = QLabel("72px");
        l_view.addWidget(self.lbl_size_val)
        l_view.addSpacing(20);
        l_view.addWidget(QLabel("排序:"))
        self.combo_sort = QComboBox();
        self.combo_sort.addItems(["名称 (A-Z)", "热度", "时间"])
        self.combo_sort.currentIndexChanged.connect(self.save_settings)
        l_view.addWidget(self.combo_sort);
        l_view.addSpacing(20)
        self.chk_badge = QCheckBox("显示来源角标");
        self.chk_badge.toggled.connect(self.save_settings)
        l_view.addWidget(self.chk_badge);
        l_view.addStretch()
        layout.addWidget(g_view)

        # 交互设置
        g_act = QGroupBox("交互行为")
        l_act = QHBoxLayout(g_act)
        self.rdo_double = QCheckBox("双击启动 (默认)");
        self.rdo_double.setChecked(True);
        self.rdo_double.setEnabled(False)
        l_act.addWidget(self.rdo_double);
        l_act.addStretch()
        layout.addWidget(g_act)

        layout.addStretch()

        btn_db = QPushButton("📂 打开数据库高级管理 (Table View)")
        btn_db.setMinimumHeight(50)
        btn_db.setStyleSheet("font-size: 11pt; font-weight: bold;")
        btn_db.clicked.connect(lambda: DatabaseDialog(self).exec())
        layout.addWidget(btn_db)

    def load_ui_states(self):
        s = self.config['Settings']
        v = s.getint('launcher_icon_size', 72);
        self.slider_size.setValue(v);
        self.lbl_size_val.setText(f"{v}px")
        self.chk_badge.setChecked(s.getboolean('launcher_show_badges', True))
        m = {'name': 0, 'count': 1, 'added': 2};
        self.combo_sort.setCurrentIndex(m.get(s.get('launcher_sort_by', 'name'), 0))
        self.slider_size.valueChanged.connect(lambda v: self.lbl_size_val.setText(f"{v}px"))

    def save_settings(self):
        s = self.config['Settings']
        s['launcher_icon_size'] = str(self.slider_size.value())
        s['launcher_show_badges'] = str(self.chk_badge.isChecked())
        s['launcher_sort_by'] = ['name', 'count', 'added'][self.combo_sort.currentIndex()]
        backend.save_config(self.config)
        self.sig_settings_changed.emit()

    def load_data(self): pass  # 占位，兼容旧接口