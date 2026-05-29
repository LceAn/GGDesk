from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QGroupBox, QPushButton,
    QHBoxLayout, QMessageBox, QComboBox, QTextEdit, QApplication
)
from PySide6.QtCore import Qt
import scanner_backend as backend


class ModelConfigPage(QWidget):
    """
    AI 分类预设管理页面。
    目前为本地分类规则管理，为后续接入 LLM API 做准备。
    未来版本将支持：
    - AI 自动分类 (Phase 4: v2.0)
    - 自定义提示词模板
    - 智能清洗 (Phase 4: v2.2)
    """

    def __init__(self):
        super().__init__()
        self.config = backend.load_config()
        self.build_ui()

    def build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)

        # 标题
        lbl_title = QLabel("🤖 智能分类 (Smart Categorization)")
        lbl_title.setStyleSheet("font-size: 16pt; font-weight: bold; color: #333;")
        layout.addWidget(lbl_title, 0, Qt.AlignmentFlag.AlignBottom)

        # 1. 分类规则
        g_categories = QGroupBox("分类规则管理")
        cat_layout = QVBoxLayout(g_categories)

        hint = QLabel("为程序设置分类标签，方便在快捷启动页面进行筛选。\n"
                       "未来将支持 AI 自动分类 (Phase 4)。")
        hint.setStyleSheet("color: #888; font-size: 9pt;")
        cat_layout.addWidget(hint)

        # 当前分类列表
        self.lbl_categories = QLabel()
        self.load_categories_text()
        cat_layout.addWidget(self.lbl_categories)

        # 操作按钮
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        btn_add = QPushButton("➕ 新增分类")
        btn_add.setObjectName("primaryButton")
        btn_add.clicked.connect(self.add_category)
        btn_row.addWidget(btn_add)

        btn_row.addStretch()
        cat_layout.addLayout(btn_row)

        layout.addWidget(g_categories)

        # 2. API 预留
        g_api = QGroupBox("AI 服务配置 (未来版本)")
        api_layout = QVBoxLayout(g_api)

        api_hint = QLabel("此功能将在 Phase 4 (v2.0) 中实装。\n"
                          "计划支持 OpenAI / Claude / 本地模型接入。")
        api_hint.setStyleSheet("color: #999; font-size: 10pt;")
        api_layout.addWidget(api_hint)

        api_row = QHBoxLayout()
        api_row.addWidget(QLabel("模型提供商:"))
        self.cb_provider = QComboBox()
        self.cb_provider.addItems(["(未配置)", "OpenAI", "Anthropic Claude", "本地 Ollama"])
        self.cb_provider.setEnabled(False)
        api_row.addWidget(self.cb_provider)
        api_row.addStretch()
        api_layout.addLayout(api_row)

        layout.addWidget(g_api)

        layout.addStretch()

    def load_categories_text(self):
        """显示当前数据库中的分类"""
        categories = self.get_existing_categories()
        if not categories:
            self.lbl_categories.setText("暂无自定义分类。点击下方按钮创建。")
            self.lbl_categories.setStyleSheet("color: #999; font-size: 10pt; padding: 10px;")
        else:
            self.lbl_categories.setText("  |  ".join(f"📁 {cat}" for cat in categories))
            self.lbl_categories.setStyleSheet("color: #333; font-size: 10pt; padding: 10px; "
                                               "background: #F5F7FA; border-radius: 6px;")

    def get_existing_categories(self):
        """从数据库获取已存在的分类"""
        try:
            import sqlite3
            conn = sqlite3.connect(backend.DB_FILE_USER)
            c = conn.cursor()
            c.execute("SELECT name FROM categories ORDER BY sort_order")
            rows = c.fetchall()
            conn.close()
            return [row[0] for row in rows]
        except Exception:
            return []

    def add_category(self):
        """通过弹窗添加新分类"""
        from PySide6.QtWidgets import QDialog, QLineEdit, QDialogButtonBox

        dialog = QDialog(self)
        dialog.setWindowTitle("新增分类")
        dialog.setWindowFlags(dialog.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        dialog_layout = QVBoxLayout(dialog)
        dialog_layout.addWidget(QLabel("请输入分类名称:"))

        edit = QLineEdit()
        edit.setPlaceholderText("例如: 开发工具、设计软件、游戏")
        dialog_layout.addWidget(edit)

        btn_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btn_box.accepted.connect(dialog.accept)
        btn_box.rejected.connect(dialog.reject)
        dialog_layout.addWidget(btn_box)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            name = edit.text().strip()
            if not name:
                return
            try:
                import sqlite3
                conn = sqlite3.connect(backend.DB_FILE_USER)
                c = conn.cursor()
                c.execute("INSERT OR IGNORE INTO categories (name) VALUES (?)", (name,))
                conn.commit()
                conn.close()
                self.load_categories_text()
            except Exception as e:
                QMessageBox.warning(self, "错误", f"添加分类失败: {e}")

    def load_data(self):
        """页面切换时刷新"""
        self.load_categories_text()
