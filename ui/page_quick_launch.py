from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QListWidget, QListWidgetItem,
    QMenu, QMessageBox, QFileIconProvider, QFrame, QApplication, QStyle
)
from PySide6.QtCore import Qt, QSize, QFileInfo
from PySide6.QtGui import QIcon, QAction
import os
import subprocess
import scanner_backend as backend


class QuickLaunchPage(QWidget):
    def __init__(self):
        super().__init__()
        self.build_ui()

    def build_ui(self):
        layout = QVBoxLayout(self);
        layout.setContentsMargins(20, 20, 20, 20);
        layout.setSpacing(10)

        # 1. 头部欢迎语 (淡雅风格)
        self.lbl_header = QLabel("👋 嗨，准备启动什么？")
        self.lbl_header.setStyleSheet("font-size: 22pt; font-weight: 300; color: #555; margin-bottom: 10px;")
        layout.addWidget(self.lbl_header)

        # 2. 图标列表 (极简风)
        self.list_widget = QListWidget()
        self.list_widget.setViewMode(QListWidget.IconMode)
        self.list_widget.setResizeMode(QListWidget.Adjust)
        self.list_widget.setMovement(QListWidget.Static)
        self.list_widget.setSpacing(12)

        # QSS: 透明背景，悬停圆角，选中微变
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

    def load_data(self):
        self.list_widget.clear()
        config = backend.load_config()

        # 1. 读取外观设置
        size_px = config.getint('Settings', 'launcher_icon_size', fallback=72)
        self.list_widget.setIconSize(QSize(size_px, size_px))
        # 网格大小稍微比图标大一点，留出文字空间
        self.list_widget.setGridSize(QSize(size_px + 40, size_px + 60))

        # 2. 读取数据
        shortcuts = backend.get_all_shortcuts()

        # 3. 排序逻辑
        sort_mode = config.get('Settings', 'launcher_sort_by', fallback='name')
        if sort_mode == 'count':
            shortcuts.sort(key=lambda x: x['run_count'], reverse=True)  # 热度降序
        elif sort_mode == 'added':
            pass  # 默认就是按时间 (added_at)
        else:
            shortcuts.sort(key=lambda x: x['name'].lower())  # 名称升序

        provider = QFileIconProvider()

        for row in shortcuts:
            name = row['name'];
            exe = row['exe_path'];
            lnk = row['lnk_path'];
            src = row['source_type']
            sid = row['id'];
            args = row['args']

            item = QListWidgetItem(name)
            item.setTextAlignment(Qt.AlignCenter)
            item.setData(Qt.UserRole, sid);
            item.setData(Qt.UserRole + 1, exe)
            item.setData(Qt.UserRole + 2, args);
            item.setData(Qt.UserRole + 3, src)

            # 图标
            icon_target = lnk if os.path.exists(lnk) else exe
            if src == 'uwp':
                item.setIcon(QApplication.style().standardIcon(QStyle.StandardPixmap.SP_DesktopIcon))
            else:
                item.setIcon(provider.icon(QFileInfo(icon_target)))

            # TODO: 如果 show_badges 为真，这里应该绘制角标 (Beta 8)

            self.list_widget.addItem(item)

    def launch_app(self, item):
        exe_path = item.data(Qt.UserRole + 1);
        args = item.data(Qt.UserRole + 2)
        source = item.data(Qt.UserRole + 3);
        sid = item.data(Qt.UserRole)
        try:
            if source == 'uwp':
                # UWP args 格式: shell:AppsFolder\Package!AppId
                uwp_target = args.replace('shell:AppsFolder\\', 'shell:AppsFolder\\') if 'shell:AppsFolder' in args else args
                subprocess.Popen(f'explorer.exe {uwp_target}')
            else:
                os.startfile(exe_path)
            backend.increment_run_count(sid)
        except Exception as e:
            QMessageBox.warning(self, "启动失败", str(e))

    def show_context_menu(self, pos):
        item = self.list_widget.itemAt(pos)
        if not item: return
        menu = QMenu();
        menu.setStyleSheet(
            "QMenu { background: white; border: 1px solid #ccc; padding: 5px; } QMenu::item { padding: 5px 20px; } QMenu::item:selected { background: #eee; }")

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