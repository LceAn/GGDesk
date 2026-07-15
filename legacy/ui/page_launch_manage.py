from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QDialog,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSlider,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

import scanner_backend as backend
from .icon_utils import shortcut_icon


class DatabaseDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("快捷方式数据库")
        self.resize(920, 620)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)
        self.build_ui()
        self.load_data()

    def build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["ID", "名称", "分类", "来源", "路径", "次数"])
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.table)

        btn_box = QHBoxLayout()
        btn_del = QPushButton("删除选中")
        btn_del.setObjectName("dangerButton")
        btn_del.clicked.connect(self.delete_selected)
        btn_close = QPushButton("关闭")
        btn_close.clicked.connect(self.accept)
        btn_box.addStretch()
        btn_box.addWidget(btn_del)
        btn_box.addWidget(btn_close)
        layout.addLayout(btn_box)

    def load_data(self):
        data = backend.get_all_shortcuts()
        self.table.setRowCount(len(data))
        for i, row in enumerate(data):
            id_item = QTableWidgetItem(str(row['id']))
            id_item.setData(Qt.ItemDataRole.UserRole, row['id'])
            self.table.setItem(i, 0, id_item)
            name_item = QTableWidgetItem(row['name'])
            name_item.setIcon(shortcut_icon(row['exe_path'], row['lnk_path'], row['source_type']))
            self.table.setItem(i, 1, name_item)
            self.table.setItem(i, 2, QTableWidgetItem(row['category'] or "默认"))
            self.table.setItem(i, 3, QTableWidgetItem(row['source_type']))
            self.table.setItem(i, 4, QTableWidgetItem(row['exe_path'] or ""))
            self.table.setItem(i, 5, QTableWidgetItem(str(row['run_count'])))

    def delete_selected(self):
        rows = sorted(set(i.row() for i in self.table.selectedItems()), reverse=True)
        if not rows:
            return
        if QMessageBox.question(
            self, "确认", f"删除 {len(rows)} 项?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        ) == QMessageBox.StandardButton.No:
            return
        for row in rows:
            backend.delete_shortcut(int(self.table.item(row, 0).text()))
        self.load_data()


class LaunchManagePage(QWidget):
    sig_settings_changed = Signal()

    def __init__(self):
        super().__init__()
        self.config = backend.load_config()
        self._loading = False
        self.build_ui()
        self.load_ui_states()
        self.load_data()

    def build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 26, 28, 26)
        layout.setSpacing(18)

        title = QLabel("⚙️ 快捷页设置")
        title.setObjectName("pageTitle")
        layout.addWidget(title, 0, Qt.AlignmentFlag.AlignBottom)

        self.tabs = QTabWidget()
        self.tabs.addTab(self.build_appearance_tab(), "外观与行为")
        self.tabs.addTab(self.build_category_tab(), "分类管理")
        self.tabs.addTab(self.build_data_tab(), "数据")
        layout.addWidget(self.tabs)

    def build_appearance_tab(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(8, 16, 8, 8)
        layout.setSpacing(16)

        g_view = QGroupBox("快捷页外观")
        l_view = QHBoxLayout(g_view)
        l_view.addWidget(QLabel("图标大小:"))
        self.slider_size = QSlider(Qt.Orientation.Horizontal)
        self.slider_size.setRange(48, 128)
        self.slider_size.setFixedWidth(180)
        self.slider_size.valueChanged.connect(self.save_settings)
        l_view.addWidget(self.slider_size)
        self.lbl_size_val = QLabel("72px")
        self.lbl_size_val.setObjectName("metricLabel")
        l_view.addWidget(self.lbl_size_val)
        l_view.addSpacing(20)
        l_view.addWidget(QLabel("排序:"))
        self.combo_sort = QComboBox()
        self.combo_sort.addItems(["名称 (A-Z)", "热度", "添加时间"])
        self.combo_sort.currentIndexChanged.connect(self.save_settings)
        l_view.addWidget(self.combo_sort)
        l_view.addSpacing(20)
        self.chk_badge = QCheckBox("显示来源/分类提示")
        self.chk_badge.toggled.connect(self.save_settings)
        l_view.addWidget(self.chk_badge)
        l_view.addStretch()
        layout.addWidget(g_view)

        g_act = QGroupBox("交互行为")
        l_act = QVBoxLayout(g_act)
        self.rdo_double = QCheckBox("双击启动")
        self.rdo_double.setChecked(True)
        self.rdo_double.setEnabled(False)
        l_act.addWidget(self.rdo_double)
        hint = QLabel("右键菜单支持运行、管理员运行、打开位置、移动分类和移除。")
        hint.setObjectName("captionLabel")
        l_act.addWidget(hint)
        layout.addWidget(g_act)
        layout.addStretch()
        return page

    def build_category_tab(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(8, 16, 8, 8)
        layout.setSpacing(16)

        top = QHBoxLayout()
        g_cat = QGroupBox("分类")
        cat_layout = QVBoxLayout(g_cat)
        self.category_combo = QComboBox()
        cat_layout.addWidget(self.category_combo)
        self.category_edit = QLineEdit()
        self.category_edit.setPlaceholderText("输入分类名称")
        cat_layout.addWidget(self.category_edit)
        cat_buttons = QHBoxLayout()
        btn_add = QPushButton("新增")
        btn_add.clicked.connect(self.add_category)
        btn_rename = QPushButton("重命名")
        btn_rename.clicked.connect(self.rename_category)
        btn_delete = QPushButton("删除")
        btn_delete.setObjectName("warningButton")
        btn_delete.clicked.connect(self.delete_category)
        cat_buttons.addWidget(btn_add)
        cat_buttons.addWidget(btn_rename)
        cat_buttons.addWidget(btn_delete)
        cat_layout.addLayout(cat_buttons)
        top.addWidget(g_cat, 1)

        g_ai = QGroupBox("智能分类")
        ai_layout = QVBoxLayout(g_ai)
        ai_desc = QLabel("根据快捷方式名称、路径和来源自动建议分类。当前为本地智能识别，后续可接入模型配置。")
        ai_desc.setObjectName("captionLabel")
        ai_desc.setWordWrap(True)
        ai_layout.addWidget(ai_desc)
        btn_ai = QPushButton("一键智能分类")
        btn_ai.setObjectName("primaryButton")
        btn_ai.clicked.connect(self.auto_classify)
        ai_layout.addWidget(btn_ai)
        top.addWidget(g_ai, 1)
        layout.addLayout(top)

        assign_bar = QHBoxLayout()
        assign_bar.addWidget(QLabel("选中快捷方式移动到:"))
        self.assign_combo = QComboBox()
        assign_bar.addWidget(self.assign_combo)
        btn_apply = QPushButton("应用到选中")
        btn_apply.clicked.connect(self.apply_category_to_selected)
        assign_bar.addWidget(btn_apply)
        assign_bar.addStretch()
        btn_refresh = QPushButton("刷新")
        btn_refresh.setObjectName("subtleButton")
        btn_refresh.clicked.connect(self.load_data)
        assign_bar.addWidget(btn_refresh)
        layout.addLayout(assign_bar)

        self.shortcut_table = QTableWidget()
        self.shortcut_table.setColumnCount(5)
        self.shortcut_table.setHorizontalHeaderLabels(["名称", "分类", "来源", "路径", "次数"])
        self.shortcut_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.shortcut_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.shortcut_table.setAlternatingRowColors(True)
        self.shortcut_table.verticalHeader().setVisible(False)
        header = self.shortcut_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.shortcut_table)
        return page

    def build_data_tab(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(8, 16, 8, 8)
        layout.setSpacing(16)

        g_db = QGroupBox("数据库")
        db_layout = QVBoxLayout(g_db)
        db_layout.addWidget(QLabel("查看、删除和排查快捷方式原始记录。"))
        btn_db = QPushButton("打开数据库高级管理")
        btn_db.setObjectName("primaryButton")
        btn_db.setMinimumHeight(44)
        btn_db.clicked.connect(lambda: DatabaseDialog(self).exec())
        db_layout.addWidget(btn_db)
        layout.addWidget(g_db)
        layout.addStretch()
        return page

    def load_ui_states(self):
        self._loading = True
        s = self.config['Settings']
        value = s.getint('launcher_icon_size', 72)
        self.slider_size.setValue(value)
        self.lbl_size_val.setText(f"{value}px")
        self.chk_badge.setChecked(s.getboolean('launcher_show_badges', True))
        index_map = {'name': 0, 'count': 1, 'added': 2}
        self.combo_sort.setCurrentIndex(index_map.get(s.get('launcher_sort_by', 'name'), 0))
        self._loading = False

    def save_settings(self):
        if self._loading:
            return
        s = self.config['Settings']
        s['launcher_icon_size'] = str(self.slider_size.value())
        s['launcher_show_badges'] = str(self.chk_badge.isChecked())
        s['launcher_sort_by'] = ['name', 'count', 'added'][self.combo_sort.currentIndex()]
        self.lbl_size_val.setText(f"{self.slider_size.value()}px")
        backend.save_config(self.config)
        self.sig_settings_changed.emit()

    def load_data(self):
        self.load_categories()
        self.load_shortcut_table()

    def load_categories(self):
        categories = backend.get_categories()
        for combo in (self.category_combo, self.assign_combo):
            current = combo.currentText()
            combo.blockSignals(True)
            combo.clear()
            combo.addItems(categories)
            index = combo.findText(current)
            combo.setCurrentIndex(index if index >= 0 else 0)
            combo.blockSignals(False)

    def load_shortcut_table(self):
        data = backend.get_all_shortcuts()
        self.shortcut_table.setRowCount(len(data))
        for row_index, row in enumerate(data):
            name_item = QTableWidgetItem(row['name'])
            name_item.setIcon(shortcut_icon(row['exe_path'], row['lnk_path'], row['source_type']))
            name_item.setData(Qt.ItemDataRole.UserRole, row['id'])
            self.shortcut_table.setItem(row_index, 0, name_item)
            self.shortcut_table.setItem(row_index, 1, QTableWidgetItem(row['category'] or "默认"))
            self.shortcut_table.setItem(row_index, 2, QTableWidgetItem(row['source_type']))
            self.shortcut_table.setItem(row_index, 3, QTableWidgetItem(row['exe_path'] or ""))
            self.shortcut_table.setItem(row_index, 4, QTableWidgetItem(str(row['run_count'])))

    def add_category(self):
        ok, msg = backend.add_category(self.category_edit.text())
        if not ok:
            QMessageBox.warning(self, "分类", msg)
            return
        self.category_edit.clear()
        self.load_data()

    def rename_category(self):
        old = self.category_combo.currentText()
        new = self.category_edit.text()
        ok, msg = backend.rename_category(old, new)
        if not ok:
            QMessageBox.warning(self, "分类", msg)
            return
        self.category_edit.clear()
        self.load_data()
        self.sig_settings_changed.emit()

    def delete_category(self):
        name = self.category_combo.currentText()
        if QMessageBox.question(
            self, "删除分类", f"删除分类“{name}”？其中快捷方式会移回默认分类。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        ) == QMessageBox.StandardButton.No:
            return
        ok, msg = backend.delete_category(name)
        if not ok:
            QMessageBox.warning(self, "分类", msg)
            return
        self.load_data()
        self.sig_settings_changed.emit()

    def apply_category_to_selected(self):
        category = self.assign_combo.currentText()
        rows = sorted(set(item.row() for item in self.shortcut_table.selectedItems()))
        if not rows:
            QMessageBox.information(self, "分类", "请先选择快捷方式。")
            return
        for row in rows:
            shortcut_id = self.shortcut_table.item(row, 0).data(Qt.ItemDataRole.UserRole)
            backend.update_shortcut_category(shortcut_id, category)
        self.load_data()
        self.sig_settings_changed.emit()

    def auto_classify(self):
        shortcuts = backend.get_all_shortcuts()
        if not shortcuts:
            QMessageBox.information(self, "智能分类", "当前没有可分类的快捷方式。")
            return
        changed = 0
        suggestions = backend.suggest_categories_for_shortcuts(shortcuts)
        for row in shortcuts:
            suggested = suggestions.get(row['id'], "默认")
            if suggested and suggested != (row['category'] or "默认"):
                if backend.update_shortcut_category(row['id'], suggested):
                    changed += 1
        self.load_data()
        self.sig_settings_changed.emit()
        QMessageBox.information(self, "智能分类", f"已更新 {changed} 个快捷方式的分类建议。")
