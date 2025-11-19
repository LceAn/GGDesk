# scanner_styles.py
"""
存放所有的 QSS 样式表定义
"""

COMMON_QSS = """
/* 全局字体与基础 */
QWidget { font-family: "Segoe UI", "Microsoft YaHei UI", sans-serif; font-size: 10pt; }

/* 红色停止按钮 */
QPushButton[objectName="stopButton"] {
    background-color: #E81123; color: white; border: none; font-weight: bold;
    border-radius: 6px; padding: 8px 16px;
}
QPushButton[objectName="stopButton"]:hover { background-color: #F03A4A; }
QPushButton[objectName="stopButton"]:pressed { background-color: #C00E1C; }

/* 主按钮 (蓝色) */
QPushButton[objectName="primaryButton"] {
    background-color: #0067C0; color: white; border: none; font-weight: bold;
    border-radius: 6px; padding: 8px 16px;
}
QPushButton[objectName="primaryButton"]:hover { background-color: #197CCC; }
QPushButton[objectName="primaryButton"]:pressed { background-color: #005299; }
QPushButton[objectName="primaryButton"]:disabled { background-color: #CCCCCC; color: #666666; }

/* 通用圆角输入框 */
QLineEdit, QTextEdit, QComboBox {
    border-radius: 6px; padding: 6px; border: 1px solid #CCCCCC;
}
"""

LIGHT_QSS = COMMON_QSS + """
QMainWindow { background-color: #F3F3F3; }
QWidget[objectName="sidebar"] { background-color: #FFFFFF; border-right: 1px solid #E5E5E5; }
QWidget[objectName="mainArea"] { background-color: #FFFFFF; border-radius: 8px; margin: 10px; }

QPushButton[objectName="navButton"] {
    background-color: transparent; color: #333333; border: none;
    padding: 12px 15px; text-align: left; border-radius: 6px; margin: 4px 8px; font-size: 11pt;
}
QPushButton[objectName="navButton"]:hover { background-color: #F0F0F0; }
QPushButton[objectName="navButton"]:checked { background-color: #E0E0E0; color: #000000; font-weight: 600; }

QPushButton { background-color: #FFFFFF; border: 1px solid #D0D0D0; border-radius: 6px; padding: 6px 12px; color: #333333; }
QPushButton:hover { background-color: #F9F9F9; border-color: #B0B0B0; }

QTreeWidget { border: 1px solid #E5E5E5; border-radius: 6px; alternate-background-color: #FAFAFA; }
QTreeWidget::item { height: 28px; }
QTreeWidget::item:selected { background-color: #E0EEF9; color: #000000; }
QHeaderView::section { background-color: #FFFFFF; border: none; border-bottom: 1px solid #E5E5E5; padding: 8px; font-weight: bold; color: #555555; }
"""

DARK_QSS = COMMON_QSS + """
QMainWindow { background-color: #202020; }
QWidget[objectName="sidebar"] { background-color: #2D2D2D; border-right: 1px solid #383838; }
QWidget[objectName="mainArea"] { background-color: #2D2D2D; border-radius: 8px; margin: 10px; }

QPushButton[objectName="navButton"] {
    background-color: transparent; color: #CCCCCC; border: none;
    padding: 12px 15px; text-align: left; border-radius: 6px; margin: 4px 8px; font-size: 11pt;
}
QPushButton[objectName="navButton"]:hover { background-color: #383838; }
QPushButton[objectName="navButton"]:checked { background-color: #404040; color: #FFFFFF; font-weight: 600; }

QPushButton { background-color: #383838; border: 1px solid #484848; border-radius: 6px; padding: 6px 12px; color: #F0F0F0; }
QPushButton:hover { background-color: #404040; }

QLineEdit, QTextEdit, QComboBox { background-color: #383838; border: 1px solid #484848; color: #F0F0F0; }

QTreeWidget { background-color: #1E1E1E; border: 1px solid #383838; border-radius: 6px; alternate-background-color: #252525; color: #F0F0F0; }
QTreeWidget::item { height: 28px; }
QTreeWidget::item:selected { background-color: #005FB8; color: #FFFFFF; }
QHeaderView::section { background-color: #2D2D2D; border: none; border-bottom: 1px solid #383838; padding: 8px; font-weight: bold; color: #CCCCCC; }
"""