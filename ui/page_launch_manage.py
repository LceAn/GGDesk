from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QTableWidget, QTableWidgetItem,
    QPushButton, QHBoxLayout, QHeaderView, QMessageBox, QAbstractItemView,
    QGroupBox, QSlider, QComboBox, QCheckBox, QApplication, QStyle
)
from PySide6.QtCore import Qt, Signal
import scanner_backend as backend


class LaunchManagePage(QWidget):
    # 信号：设置改变时通知 QuickLaunch 页刷新
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

        # --- 1. 视觉与交互设置 (Settings) ---
        layout.addWidget(QLabel("🎨 启动页外观与行为"), 0, Qt.AlignmentFlag.AlignBottom)

        g_view = QGroupBox("视图设置")
        l_view = QHBoxLayout(g_view)

        # 图标大小滑块
        l_view.addWidget(QLabel("图标大小:"))
        self.slider_size = QSlider(Qt.Orientation.Horizontal)
        self.slider_size.setRange(48, 128)  # 48px - 128px
        self.slider_size.setFixedWidth(150)
        self.slider_size.valueChanged.connect(self.save_settings)
        l_view.addWidget(self.slider_size)
        self.lbl_size_val = QLabel("72px")
        l_view.addWidget(self.lbl_size_val)

        l_view.addSpacing(20)

        # 排序方式
        l_view.addWidget(QLabel("排序方式:"))
        self.combo_sort = QComboBox()
        self.combo_sort.addItems(["按名称 (A-Z)", "按启动次数 (热度)", "按添加时间 (最新)"])
        self.combo_sort.currentIndexChanged.connect(self.save_settings)
        l_view.addWidget(self.combo_sort)

        l_view.addSpacing(20)

        # 角标开关
        self.chk_badge = QCheckBox("显示来源角标")
        self.chk_badge.toggled.connect(self.save_settings)
        l_view.addWidget(self.chk_badge)

        l_view.addStretch()
        layout.addWidget(g_view)

        # --- 2. 数据库列表 (Database) ---
        layout.addWidget(QLabel("🛠️ 数据库管理"), 0, Qt.AlignmentFlag.AlignBottom)

        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["ID", "程序名称", "来源类型", "可执行路径", "启动次数"])
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setStyleSheet("border: 1px solid #CCC; border-radius: 6px;")

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.Stretch)

        layout.addWidget(self.table)

        btn_box = QHBoxLayout()
        btn_refresh = QPushButton("🔄 刷新列表");
        btn_refresh.clicked.connect(self.load_data)
        btn_del = QPushButton("🗑️ 删除选中项");
        btn_del.setStyleSheet("background-color: #FFF0F0; color: #D94430; border: 1px solid #E5C0C0;")
        btn_del.clicked.connect(self.delete_selected)

        btn_box.addStretch()
        btn_box.addWidget(btn_refresh)
        btn_box.addWidget(btn_del)
        layout.addLayout(btn_box)

    def load_ui_states(self):
        settings = self.config['Settings']
        # Size
        size = settings.getint('launcher_icon_size', 72)
        self.slider_size.setValue(size)
        self.lbl_size_val.setText(f"{size}px")
        # Badge
        self.chk_badge.setChecked(settings.getboolean('launcher_show_badges', True))
        # Sort
        sort_map = {'name': 0, 'count': 1, 'added': 2}
        self.combo_sort.setCurrentIndex(sort_map.get(settings.get('launcher_sort_by', 'name'), 0))

        # Slider label update linkage
        self.slider_size.valueChanged.connect(lambda v: self.lbl_size_val.setText(f"{v}px"))

    def save_settings(self):
        # 保存配置并发送信号通知 QuickLaunch 页刷新
        settings = self.config['Settings']
        settings['launcher_icon_size'] = str(self.slider_size.value())
        settings['launcher_show_badges'] = str(self.chk_badge.isChecked())

        idx = self.combo_sort.currentIndex()
        sort_vals = ['name', 'count', 'added']
        settings['launcher_sort_by'] = sort_vals[idx]

        backend.save_config(self.config)
        self.sig_settings_changed.emit()  # 通知主窗口转发

    def load_data(self):
        self.table.setRowCount(0)
        try:
            data = backend.get_all_shortcuts()
            self.table.setRowCount(len(data))
            for i, row in enumerate(data):
                self.table.setItem(i, 0, QTableWidgetItem(str(row['id'])))

                # Name + Icon (简单处理，这里不加载真实图标以提升管理页速度，仅用默认)
                item_name = QTableWidgetItem(row['name'])
                if row['source_type'] == 'uwp':
                    item_name.setIcon(QApplication.style().standardIcon(QStyle.StandardPixmap.SP_DesktopIcon))
                else:
                    item_name.setIcon(QApplication.style().standardIcon(QStyle.StandardPixmap.SP_FileIcon))
                self.table.setItem(i, 1, item_name)

                self.table.setItem(i, 2, QTableWidgetItem(row['source_type']))
                self.table.setItem(i, 3, QTableWidgetItem(row['exe_path']))
                self.table.setItem(i, 4, QTableWidgetItem(str(row['run_count'])))
        except:
            pass

    def delete_selected(self):
        rows = sorted(set(i.row() for i in self.table.selectedItems()), reverse=True)
        if not rows: return
        if QMessageBox.question(self, "确认", f"删除 {len(rows)} 个条目?",
                                QMessageBox.Yes | QMessageBox.No) == QMessageBox.No: return
        for r in rows:
            backend.delete_shortcut(int(self.table.item(r, 0).text()))
        self.load_data()
        self.sig_settings_changed.emit()  # 也要刷新首页