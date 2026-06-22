import os
import subprocess

from PySide6.QtCore import Qt, QSize
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QMessageBox,
    QStyle,
    QVBoxLayout,
    QWidget,
)

import scanner_backend as backend
from .icon_utils import is_shell_app_id, shortcut_icon


class QuickLaunchPage(QWidget):
    def __init__(self):
        super().__init__()
        self.shortcuts = []
        self.build_ui()

    def build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 26, 28, 26)
        layout.setSpacing(18)

        header = QHBoxLayout()
        self.lbl_header = QLabel("👋 嗨，准备启动什么？")
        self.lbl_header.setObjectName("pageTitle")
        header.addWidget(self.lbl_header)
        header.addStretch()

        self.category_combo = QComboBox()
        self.category_combo.setMinimumWidth(150)
        self.category_combo.currentTextChanged.connect(self.apply_filters)
        header.addWidget(QLabel("分类:"))
        header.addWidget(self.category_combo)

        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("搜索快捷方式")
        self.search_edit.setClearButtonEnabled(True)
        self.search_edit.setMinimumWidth(220)
        self.search_edit.textChanged.connect(self.apply_filters)
        header.addWidget(self.search_edit)
        layout.addLayout(header)

        self.empty_label = QLabel("还没有快捷方式。先去“扫描程序”添加应用。")
        self.empty_label.setObjectName("captionLabel")
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_label.setMinimumHeight(180)
        layout.addWidget(self.empty_label)

        self.list_widget = QListWidget()
        self.list_widget.setViewMode(QListWidget.IconMode)
        self.list_widget.setResizeMode(QListWidget.Adjust)
        self.list_widget.setMovement(QListWidget.Static)
        self.list_widget.setSpacing(10)
        self.list_widget.itemDoubleClicked.connect(self.launch_app)
        self.list_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.list_widget.customContextMenuRequested.connect(self.show_context_menu)
        layout.addWidget(self.list_widget)

    def load_data(self):
        config = backend.load_config()
        size_px = config.getint('Settings', 'launcher_icon_size', fallback=72)
        self.list_widget.setIconSize(QSize(size_px, size_px))
        self.list_widget.setGridSize(QSize(size_px + 48, size_px + 70))

        self.shortcuts = list(backend.get_all_shortcuts())
        self.refresh_category_filter()
        self.apply_filters()

    def refresh_category_filter(self):
        current = self.category_combo.currentText() or "全部"
        categories = backend.get_categories(include_all=True)
        self.category_combo.blockSignals(True)
        self.category_combo.clear()
        self.category_combo.addItems(categories)
        index = self.category_combo.findText(current)
        self.category_combo.setCurrentIndex(index if index >= 0 else 0)
        self.category_combo.blockSignals(False)

    def apply_filters(self):
        self.list_widget.clear()
        category = self.category_combo.currentText() or "全部"
        query = self.search_edit.text().strip().lower()
        config = backend.load_config()
        sort_mode = config.get('Settings', 'launcher_sort_by', fallback='name')
        show_badges = config.getboolean('Settings', 'launcher_show_badges', fallback=True)

        items = list(self.shortcuts)
        if category != "全部":
            items = [row for row in items if (row['category'] or "默认") == category]
        if query:
            items = [
                row for row in items
                if query in row['name'].lower()
                or query in (row['exe_path'] or '').lower()
                or query in (row['category'] or '').lower()
            ]

        if sort_mode == 'count':
            items.sort(key=lambda x: x['run_count'], reverse=True)
        elif sort_mode == 'added':
            pass
        else:
            items.sort(key=lambda x: x['name'].lower())

        has_shortcuts = bool(items)
        self.empty_label.setVisible(not has_shortcuts)
        self.list_widget.setVisible(has_shortcuts)
        if not self.shortcuts:
            self.empty_label.setText("还没有快捷方式。先去“扫描程序”添加应用。")
        elif not items:
            self.empty_label.setText("没有匹配当前分类或搜索条件的快捷方式。")

        for row in items:
            item = QListWidgetItem(row['name'])
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item.setIcon(shortcut_icon(
                row['exe_path'],
                row['lnk_path'],
                row['source_type'],
                QApplication.style().standardIcon(QStyle.StandardPixmap.SP_DesktopIcon)
            ))
            item.setToolTip(
                f"{row['name']}\n分类: {row['category'] or '默认'}\n来源: {row['source_type']}\n路径: {row['exe_path']}"
            )
            item.setData(Qt.ItemDataRole.UserRole, row['id'])
            item.setData(Qt.ItemDataRole.UserRole + 1, row['exe_path'])
            item.setData(Qt.ItemDataRole.UserRole + 2, row['args'])
            item.setData(Qt.ItemDataRole.UserRole + 3, row['source_type'])
            item.setData(Qt.ItemDataRole.UserRole + 4, row['category'] or "默认")
            if show_badges:
                item.setStatusTip(f"{row['category'] or '默认'} · {row['source_type']}")
            self.list_widget.addItem(item)

    def launch_app(self, item):
        exe_path = item.data(Qt.ItemDataRole.UserRole + 1)
        args = item.data(Qt.ItemDataRole.UserRole + 2)
        source = item.data(Qt.ItemDataRole.UserRole + 3)
        sid = item.data(Qt.ItemDataRole.UserRole)
        try:
            if source == 'uwp' and args and is_shell_app_id(exe_path):
                subprocess.Popen(['explorer.exe', args])
            else:
                os.startfile(exe_path)
            backend.increment_run_count(sid)
        except Exception as e:
            QMessageBox.warning(self, "启动失败", str(e))

    def show_context_menu(self, pos):
        item = self.list_widget.itemAt(pos)
        if not item:
            return

        menu = QMenu()
        menu.addAction("运行", lambda: self.launch_app(item))

        exe_path = item.data(Qt.ItemDataRole.UserRole + 1)
        source = item.data(Qt.ItemDataRole.UserRole + 3)
        if source != 'uwp' or not is_shell_app_id(exe_path):
            menu.addAction("管理员运行", lambda: self.run_as_admin(item))
            if exe_path and os.path.exists(exe_path):
                menu.addSeparator()
                menu.addAction("打开所在位置", lambda: subprocess.Popen(['explorer.exe', f'/select,"{exe_path}"']))

        category_menu = menu.addMenu("移动到分类")
        for category in backend.get_categories():
            category_menu.addAction(category, lambda c=category: self.move_item_to_category(item, c))

        menu.addSeparator()
        menu.addAction("移除", lambda: self.delete_item(item))
        menu.exec(self.list_widget.mapToGlobal(pos))

    def move_item_to_category(self, item, category):
        backend.update_shortcut_category(item.data(Qt.ItemDataRole.UserRole), category)
        self.load_data()

    def run_as_admin(self, item):
        try:
            import ctypes
            ctypes.windll.shell32.ShellExecuteW(
                None, "runas", item.data(Qt.ItemDataRole.UserRole + 1), None, None, 1
            )
        except Exception as e:
            QMessageBox.warning(self, "错误", str(e))

    def delete_item(self, item):
        if QMessageBox.question(
            self, "确认", f"移除 {item.text()}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        ) == QMessageBox.StandardButton.Yes:
            backend.delete_shortcut(item.data(Qt.ItemDataRole.UserRole))
            self.load_data()
