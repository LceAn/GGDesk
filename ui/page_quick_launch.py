from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QListWidget, QListWidgetItem,
    QMenu, QMessageBox, QFileIconProvider, QFrame, QApplication, QStyle,
    QLineEdit
)
from PySide6.QtCore import Qt, QSize, QFileInfo, Signal
from PySide6.QtGui import QIcon, QAction, QShortcut, QKeySequence
import os
import subprocess
import scanner_backend as backend


class QuickLaunchPage(QWidget):
    def __init__(self):
        super().__init__()
        self._all_items = []  # 缓存所有条目用于搜索过滤
        self.build_ui()

    def build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(10)

        # 1. 头部欢迎语 + 搜索框
        header_layout = QHBoxLayout()

        self.lbl_header = QLabel("👋 嗨，准备启动什么？")
        self.lbl_header.setStyleSheet("font-size: 22pt; font-weight: 300; color: #555;")
        header_layout.addWidget(self.lbl_header)

        header_layout.addStretch()

        # 搜索框
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("🔍 搜索应用...")
        self.search_edit.setFixedWidth(220)
        self.search_edit.setClearButtonEnabled(True)
        self.search_edit.textChanged.connect(self._filter_items)
        header_layout.addWidget(self.search_edit)

        layout.addLayout(header_layout)

        # 2. 图标列表
        self.list_widget = QListWidget()
        self.list_widget.setViewMode(QListWidget.IconMode)
        self.list_widget.setResizeMode(QListWidget.Adjust)
        self.list_widget.setMovement(QListWidget.Static)
        self.list_widget.setSpacing(12)

        self.list_widget.setStyleSheet("""
            QListWidget {
                background-color: transparent;
                border: none;
                outline: none;
            }
            QListWidget::item {
                background-color: transparent;
                border-radius: 10px;
                color: #333;
                padding: 5px;
            }
            QListWidget::item:hover {
                background-color: rgba(0, 0, 0, 0.05);
            }
            QListWidget::item:selected {
                background-color: rgba(0, 120, 215, 0.1);
                color: #000;
            }
        """)

        self.list_widget.itemDoubleClicked.connect(self.launch_app)
        self.list_widget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.list_widget.customContextMenuRequested.connect(self.show_context_menu)

        layout.addWidget(self.list_widget)

        # 3. 底部统计
        self.lbl_stats = QLabel("")
        self.lbl_stats.setStyleSheet("color: #999; font-size: 9pt; margin-left: 5px;")
        layout.addWidget(self.lbl_stats)

    def load_data(self):
        self.list_widget.clear()
        self._all_items = []
        config = backend.load_config()

        # 读取外观设置
        size_px = config.getint('Settings', 'launcher_icon_size', fallback=72)
        self.list_widget.setIconSize(QSize(size_px, size_px))
        self.list_widget.setGridSize(QSize(size_px + 40, size_px + 60))

        # 读取数据
        shortcuts = backend.get_all_shortcuts()

        # 排序逻辑
        sort_mode = config.get('Settings', 'launcher_sort_by', fallback='name')
        if sort_mode == 'count':
            shortcuts.sort(key=lambda x: x['run_count'], reverse=True)
        elif sort_mode == 'added':
            pass
        else:
            shortcuts.sort(key=lambda x: x['name'].lower())

        provider = QFileIconProvider()

        for row in shortcuts:
            name = row['name']
            exe = row['exe_path']
            lnk = row['lnk_path']
            src = row['source_type']
            sid = row['id']
            args = row['args']

            item = QListWidgetItem(name)
            item.setTextAlignment(Qt.AlignCenter)
            item.setData(Qt.UserRole, sid)
            item.setData(Qt.UserRole + 1, exe)
            item.setData(Qt.UserRole + 2, args)
            item.setData(Qt.UserRole + 3, src)

            # 图标
            icon_target = lnk if os.path.exists(lnk) else exe
            if src == 'uwp':
                item.setIcon(QApplication.style().standardIcon(QStyle.StandardPixmap.SP_DesktopIcon))
            else:
                item.setIcon(provider.icon(QFileInfo(icon_target)))

            self.list_widget.addItem(item)
            self._all_items.append({
                'item': item,
                'name': name.lower(),
                'exe': (exe or '').lower(),
            })

        # 更新统计
        total = len(self._all_items)
        self.lbl_stats.setText(f"共 {total} 个应用")
        self._update_stats()

    def _filter_items(self, text):
        """根据搜索关键词过滤列表"""
        query = text.lower().strip()
        visible_count = 0

        for entry in self._all_items:
            item = entry['item']
            if not query:
                item.setHidden(False)
                visible_count += 1
            else:
                match = query in entry['name'] or query in entry['exe']
                item.setHidden(not match)
                if match:
                    visible_count += 1

        self._update_stats(visible_count if query else None)

    def _update_stats(self, visible=None):
        total = len(self._all_items)
        if visible is not None and visible != total:
            self.lbl_stats.setText(f"显示 {visible} / 共 {total} 个应用")
        else:
            self.lbl_stats.setText(f"共 {total} 个应用")

    def launch_app(self, item):
        exe_path = item.data(Qt.UserRole + 1)
        args = item.data(Qt.UserRole + 2)
        source = item.data(Qt.UserRole + 3)
        sid = item.data(Qt.UserRole)
        try:
            if source == 'uwp':
                # args 格式: shell:AppsFolder\Package!AppId
                subprocess.Popen(f'explorer.exe {args}')
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
        menu.setStyleSheet(
            "QMenu { background: white; border: 1px solid #ccc; padding: 5px; } "
            "QMenu::item { padding: 5px 20px; } "
            "QMenu::item:selected { background: #eee; }")

        menu.addAction("🚀 运行", lambda: self.launch_app(item))
        menu.addAction("🛡️ 管理员运行", lambda: self.run_as_admin(item))

        if item.data(Qt.UserRole + 3) != 'uwp':
            menu.addSeparator()
            menu.addAction("📂 打开所在位置",
                           lambda: subprocess.Popen(f'explorer /select,"{item.data(Qt.UserRole + 1)}"'))

        menu.addSeparator()
        menu.addAction("🗑️ 移除", lambda: self.delete_item(item))
        menu.exec(self.list_widget.mapToGlobal(pos))

    def run_as_admin(self, item):
        try:
            import ctypes
            ctypes.windll.shell32.ShellExecuteW(None, "runas", item.data(Qt.UserRole + 1), None, None, 1)
        except Exception as e:
            QMessageBox.warning(self, "错误", str(e))

    def delete_item(self, item):
        if QMessageBox.question(self, "确认", f"移除 {item.text()}?",
                                QMessageBox.Yes | QMessageBox.No) == QMessageBox.Yes:
            backend.delete_shortcut(item.data(Qt.UserRole))
            self.load_data()
