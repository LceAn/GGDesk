"""
Global QSS for GGDesk.

The visual language is intentionally close to Google's Material surfaces:
soft white cards, Google blue as the primary action color, compact controls,
and clear focus/selection states for a desktop utility workflow.
"""

COMMON_QSS = """
* {
    font-family: "Google Sans", "Segoe UI", "Microsoft YaHei UI", sans-serif;
    font-size: 10pt;
    selection-background-color: #d2e3fc;
    selection-color: #202124;
}

QToolTip {
    background-color: #202124;
    color: #ffffff;
    border: none;
    border-radius: 4px;
    padding: 6px 8px;
}

QPushButton {
    min-height: 28px;
    padding: 6px 14px;
    border-radius: 8px;
    font-weight: 500;
}
QPushButton:disabled {
    background-color: #f1f3f4;
    color: #9aa0a6;
    border-color: #e8eaed;
}
QPushButton#primaryButton {
    min-height: 32px;
    background-color: #1a73e8;
    color: #ffffff;
    border: 1px solid #1a73e8;
}
QPushButton#primaryButton:hover {
    background-color: #1765cc;
    border-color: #1765cc;
}
QPushButton#primaryButton:pressed {
    background-color: #185abc;
    border-color: #185abc;
}
QPushButton#primaryButton:disabled {
    background-color: #e8eaed;
    color: #9aa0a6;
    border-color: #e8eaed;
}
QPushButton#stopButton,
QPushButton#dangerButton {
    background-color: #d93025;
    color: #ffffff;
    border: 1px solid #d93025;
}
QPushButton#stopButton:hover,
QPushButton#dangerButton:hover {
    background-color: #c5221f;
    border-color: #c5221f;
}

QLineEdit,
QTextEdit,
QPlainTextEdit,
QComboBox,
QSpinBox {
    min-height: 26px;
    padding: 7px 10px;
    border-radius: 8px;
}
QLineEdit:focus,
QTextEdit:focus,
QPlainTextEdit:focus,
QComboBox:focus,
QSpinBox:focus {
    border: 1px solid #1a73e8;
}
QLineEdit:disabled,
QTextEdit:disabled,
QPlainTextEdit:disabled,
QComboBox:disabled,
QSpinBox:disabled {
    color: #9aa0a6;
}

QComboBox::drop-down {
    width: 28px;
    border: none;
}
QComboBox QAbstractItemView {
    selection-background-color: #e8f0fe;
    selection-color: #202124;
    outline: none;
}

QCheckBox {
    spacing: 8px;
}

QSlider::groove:horizontal {
    height: 4px;
    border-radius: 2px;
}
QSlider::handle:horizontal {
    width: 16px;
    height: 16px;
    margin: -6px 0;
    border-radius: 8px;
}

QGroupBox {
    font-weight: 600;
    border-radius: 8px;
    margin-top: 16px;
    padding: 18px 14px 14px 14px;
}
QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 12px;
    padding: 0 8px;
}

QHeaderView::section {
    min-height: 30px;
    padding: 8px 10px;
    font-weight: 600;
}
QTreeWidget,
QTableWidget,
QListWidget {
    outline: none;
}
QTreeWidget::item,
QTableWidget::item {
    min-height: 30px;
    padding: 4px 6px;
}
QTreeWidget::branch {
    background: transparent;
}

QMenu {
    padding: 6px;
    border-radius: 8px;
}
QMenu::item {
    padding: 7px 26px 7px 12px;
    border-radius: 6px;
}
QMenu::separator {
    height: 1px;
    margin: 6px 4px;
}

QTabWidget::pane {
    border: none;
    top: -1px;
}
QTabBar::tab {
    min-width: 92px;
    min-height: 30px;
    padding: 6px 14px;
    border-radius: 8px;
    margin-right: 6px;
    font-weight: 500;
}

QScrollBar:vertical {
    width: 10px;
    margin: 2px;
    border: none;
}
QScrollBar::handle:vertical {
    min-height: 32px;
    border-radius: 5px;
}
QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical,
QScrollBar::add-page:vertical,
QScrollBar::sub-page:vertical {
    height: 0;
    background: transparent;
}
"""

LIGHT_QSS = COMMON_QSS + """
QMainWindow,
QDialog {
    background-color: #f8fafd;
    color: #202124;
}
QWidget#sidebar {
    background-color: #ffffff;
    border-right: 1px solid #e8eaed;
}
QStackedWidget#mainArea,
QWidget#mainArea {
    background-color: #f8fafd;
    border: none;
    margin: 0;
}

QLabel {
    color: #202124;
}
QLabel#pageTitle {
    font-size: 20pt;
    font-weight: 600;
    color: #202124;
}
QLabel#sectionLabel {
    font-weight: 600;
    color: #3c4043;
}
QLabel#captionLabel,
QLabel#navCategory {
    color: #5f6368;
}
QLabel#metricLabel {
    color: #1a73e8;
    font-weight: 600;
}

QPushButton {
    background-color: #ffffff;
    border: 1px solid #dadce0;
    color: #1f1f1f;
}
QPushButton:hover {
    background-color: #f8fafd;
    border-color: #c6dafc;
}
QPushButton:pressed {
    background-color: #edf2fa;
}
QPushButton#navButton {
    background-color: transparent;
    color: #3c4043;
    border: none;
    padding: 10px 12px;
    text-align: left;
    border-radius: 8px;
    margin: 2px 4px;
    font-size: 10.5pt;
}
QPushButton#navButton:hover {
    background-color: #f1f3f4;
}
QPushButton#navButton:checked {
    background-color: #e8f0fe;
    color: #174ea6;
    font-weight: 600;
}
QPushButton#brandButton {
    background-color: transparent;
    border: none;
    color: #202124;
    padding: 12px;
    text-align: left;
    font-size: 12.5pt;
    font-weight: 700;
}
QPushButton#brandButton:hover {
    background-color: #f1f3f4;
}
QPushButton#subtleButton {
    background-color: transparent;
    border-color: transparent;
    color: #1a73e8;
}
QPushButton#subtleButton:hover {
    background-color: #e8f0fe;
}
QPushButton#warningButton {
    background-color: #fce8e6;
    border-color: #fad2cf;
    color: #b3261e;
}

QLineEdit,
QTextEdit,
QPlainTextEdit,
QComboBox,
QSpinBox {
    background-color: #ffffff;
    border: 1px solid #dadce0;
    color: #202124;
}
QLineEdit[readOnly="true"] {
    background-color: #f8fafd;
    color: #5f6368;
}

QCheckBox {
    color: #3c4043;
}

QSlider::groove:horizontal {
    background-color: #dadce0;
}
QSlider::sub-page:horizontal {
    background-color: #1a73e8;
    border-radius: 2px;
}
QSlider::handle:horizontal {
    background-color: #1a73e8;
    border: 2px solid #ffffff;
}

QGroupBox {
    background-color: #ffffff;
    border: 1px solid #e8eaed;
    color: #202124;
}
QGroupBox::title {
    background-color: #f8fafd;
    color: #3c4043;
}
QFrame#pageContent {
    background-color: #ffffff;
    border: 1px solid #e8eaed;
    border-radius: 8px;
    margin: 15px;
    padding: 20px;
}
QFrame#dialogFooter {
    background-color: #ffffff;
    border-top: 1px solid #e8eaed;
}
QLabel#title {
    font-size: 32pt;
    font-weight: 700;
    color: #202124;
    margin-bottom: 10px;
}
QLabel#subtitle {
    font-size: 16pt;
    color: #1a73e8;
    margin-bottom: 30px;
}
QLabel#content {
    font-size: 11pt;
    color: #5f6368;
    line-height: 1.6;
    padding: 0 30px;
}

QTreeWidget,
QTableWidget {
    background-color: #ffffff;
    alternate-background-color: #f8fafd;
    border: 1px solid #e8eaed;
    border-radius: 8px;
    color: #202124;
    gridline-color: #e8eaed;
}
QTreeWidget::item:hover,
QTableWidget::item:hover {
    background-color: #f1f3f4;
}
QTreeWidget::item:selected,
QTableWidget::item:selected {
    background-color: #e8f0fe;
    color: #202124;
}
QHeaderView::section {
    background-color: #ffffff;
    color: #5f6368;
    border: none;
    border-bottom: 1px solid #e8eaed;
}
QListWidget {
    background-color: transparent;
    border: none;
    color: #202124;
}
QListWidget::item {
    background-color: transparent;
    border-radius: 8px;
    padding: 8px;
    color: #202124;
}
QListWidget::item:hover {
    background-color: #f1f3f4;
}
QListWidget::item:selected {
    background-color: #e8f0fe;
    color: #174ea6;
}

QMenu {
    background-color: #ffffff;
    border: 1px solid #dadce0;
    color: #202124;
}
QMenu::item:selected {
    background-color: #e8f0fe;
    color: #174ea6;
}
QMenu::separator {
    background-color: #e8eaed;
}
QTabBar::tab {
    background-color: transparent;
    color: #5f6368;
}
QTabBar::tab:hover {
    background-color: #f1f3f4;
}
QTabBar::tab:selected {
    background-color: #e8f0fe;
    color: #174ea6;
}

QStatusBar {
    background-color: #ffffff;
    border-top: 1px solid #e8eaed;
    min-height: 30px;
    color: #5f6368;
}
QStatusBar::item {
    border: none;
}
QProgressBar {
    background-color: #e8eaed;
    border: none;
    border-radius: 2px;
}
QProgressBar::chunk {
    background-color: #1a73e8;
    border-radius: 2px;
}
QFrame[frameShape="4"],
QFrame[frameShape="5"] {
    color: #e8eaed;
}
QScrollBar:vertical {
    background: #f8fafd;
}
QScrollBar::handle:vertical {
    background: #bdc1c6;
}
QScrollBar::handle:vertical:hover {
    background: #9aa0a6;
}
"""

DARK_QSS = COMMON_QSS + """
QMainWindow,
QDialog {
    background-color: #202124;
    color: #e8eaed;
}
QWidget#sidebar {
    background-color: #171717;
    border-right: 1px solid #303134;
}
QStackedWidget#mainArea,
QWidget#mainArea {
    background-color: #202124;
    border: none;
    margin: 0;
}

QLabel {
    color: #e8eaed;
}
QLabel#pageTitle {
    font-size: 20pt;
    font-weight: 600;
    color: #f1f3f4;
}
QLabel#sectionLabel {
    font-weight: 600;
    color: #f1f3f4;
}
QLabel#captionLabel,
QLabel#navCategory {
    color: #bdc1c6;
}
QLabel#metricLabel {
    color: #8ab4f8;
    font-weight: 600;
}

QPushButton {
    background-color: #2b2c2f;
    border: 1px solid #3c4043;
    color: #f1f3f4;
}
QPushButton:hover {
    background-color: #303134;
    border-color: #5f6368;
}
QPushButton:pressed {
    background-color: #3c4043;
}
QPushButton:disabled {
    background-color: #303134;
    color: #5f6368;
    border-color: #3c4043;
}
QPushButton#primaryButton {
    background-color: #8ab4f8;
    color: #202124;
    border-color: #8ab4f8;
}
QPushButton#primaryButton:hover {
    background-color: #aecbfa;
    border-color: #aecbfa;
}
QPushButton#primaryButton:pressed {
    background-color: #669df6;
    border-color: #669df6;
}
QPushButton#primaryButton:disabled {
    background-color: #303134;
    color: #5f6368;
    border-color: #3c4043;
}
QPushButton#navButton {
    background-color: transparent;
    color: #c9d1d9;
    border: none;
    padding: 10px 12px;
    text-align: left;
    border-radius: 8px;
    margin: 2px 4px;
    font-size: 10.5pt;
}
QPushButton#navButton:hover {
    background-color: #2b2c2f;
}
QPushButton#navButton:checked {
    background-color: #26354f;
    color: #d2e3fc;
    font-weight: 600;
}
QPushButton#brandButton {
    background-color: transparent;
    border: none;
    color: #f1f3f4;
    padding: 12px;
    text-align: left;
    font-size: 12.5pt;
    font-weight: 700;
}
QPushButton#brandButton:hover {
    background-color: #2b2c2f;
}
QPushButton#subtleButton {
    background-color: transparent;
    border-color: transparent;
    color: #8ab4f8;
}
QPushButton#subtleButton:hover {
    background-color: #26354f;
}
QPushButton#warningButton {
    background-color: #41201d;
    border-color: #5c2b25;
    color: #f28b82;
}

QLineEdit,
QTextEdit,
QPlainTextEdit,
QComboBox,
QSpinBox {
    background-color: #2b2c2f;
    border: 1px solid #3c4043;
    color: #f1f3f4;
}
QLineEdit[readOnly="true"] {
    background-color: #202124;
    color: #bdc1c6;
}

QCheckBox {
    color: #e8eaed;
}

QSlider::groove:horizontal {
    background-color: #5f6368;
}
QSlider::sub-page:horizontal {
    background-color: #8ab4f8;
    border-radius: 2px;
}
QSlider::handle:horizontal {
    background-color: #8ab4f8;
    border: 2px solid #202124;
}

QGroupBox {
    background-color: #2b2c2f;
    border: 1px solid #3c4043;
    color: #f1f3f4;
}
QGroupBox::title {
    background-color: #202124;
    color: #e8eaed;
}
QFrame#pageContent {
    background-color: #2b2c2f;
    border: 1px solid #3c4043;
    border-radius: 8px;
    margin: 15px;
    padding: 20px;
}
QFrame#dialogFooter {
    background-color: #171717;
    border-top: 1px solid #303134;
}
QLabel#title {
    font-size: 32pt;
    font-weight: 700;
    color: #f1f3f4;
    margin-bottom: 10px;
}
QLabel#subtitle {
    font-size: 16pt;
    color: #8ab4f8;
    margin-bottom: 30px;
}
QLabel#content {
    font-size: 11pt;
    color: #bdc1c6;
    line-height: 1.6;
    padding: 0 30px;
}

QTreeWidget,
QTableWidget {
    background-color: #2b2c2f;
    alternate-background-color: #252629;
    border: 1px solid #3c4043;
    border-radius: 8px;
    color: #f1f3f4;
    gridline-color: #3c4043;
}
QTreeWidget::item:hover,
QTableWidget::item:hover {
    background-color: #303134;
}
QTreeWidget::item:selected,
QTableWidget::item:selected {
    background-color: #26354f;
    color: #f1f3f4;
}
QHeaderView::section {
    background-color: #2b2c2f;
    color: #bdc1c6;
    border: none;
    border-bottom: 1px solid #3c4043;
}
QListWidget {
    background-color: transparent;
    border: none;
    color: #f1f3f4;
}
QListWidget::item {
    background-color: transparent;
    border-radius: 8px;
    padding: 8px;
    color: #f1f3f4;
}
QListWidget::item:hover {
    background-color: #303134;
}
QListWidget::item:selected {
    background-color: #26354f;
    color: #d2e3fc;
}

QMenu {
    background-color: #2b2c2f;
    border: 1px solid #3c4043;
    color: #f1f3f4;
}
QMenu::item:selected {
    background-color: #26354f;
    color: #d2e3fc;
}
QMenu::separator {
    background-color: #3c4043;
}
QTabBar::tab {
    background-color: transparent;
    color: #bdc1c6;
}
QTabBar::tab:hover {
    background-color: #303134;
}
QTabBar::tab:selected {
    background-color: #26354f;
    color: #d2e3fc;
}

QStatusBar {
    background-color: #171717;
    border-top: 1px solid #303134;
    min-height: 30px;
    color: #bdc1c6;
}
QStatusBar::item {
    border: none;
}
QProgressBar {
    background-color: #3c4043;
    border: none;
    border-radius: 2px;
}
QProgressBar::chunk {
    background-color: #8ab4f8;
    border-radius: 2px;
}
QFrame[frameShape="4"],
QFrame[frameShape="5"] {
    color: #3c4043;
}
QScrollBar:vertical {
    background: #202124;
}
QScrollBar::handle:vertical {
    background: #5f6368;
}
QScrollBar::handle:vertical:hover {
    background: #80868b;
}
"""
