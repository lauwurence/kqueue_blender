################################################################################
## Config Variables

DEV_MODE = False
TITLE = "kQueue Blender"
DEVELOPER = 'keyclap'
VERSION = (0, 9, 1)
APPID = f'{DEVELOPER}.{TITLE.replace(" ", "_")}.{".".join([str(v) for v in VERSION])}'.lower()

ICON = "kqueue/icons/icon.svg"
RENDER_START_AUDIO = "kqueue/audio/render_started.ogg"
RENDER_STOP_AUDIO = "kqueue/audio/render_stopped.ogg"
RENDER_FINISH_AUDIO = "kqueue/audio/render_finished.ogg"

SAVE_FOLDER = "saves/"
TEMP_FOLDER = "kqueue/blender/temp/"

CACHE_FILE = "kqueue/blender/.cache"
CRASH_FILE = "log.txt"
PERSISTENT_FILE = f"kqueue/{SAVE_FOLDER}/.persistent"
BRIDGE_FILE = f"{TEMP_FOLDER}data.json"
GET_DATA_BAT = f"{TEMP_FOLDER}get_data.bat"
GET_DATA_PY = "kqueue/blender/get_data.py"

STYLE = '''
* {
    font-family: Segoe UI, Arial, sans-serif;
}

QLabel {
    font-size: 11px;
    color: #e0e0e0;
}

QLabel:disabled {
    font-size: 11px;
    color: #707070;
}

QPushButton {
    font-size: 11px;
    background-color: #3a3a3a;
    color: #e0e0e0;
    border: 1px solid #555555;
    border-radius: 4px;
    padding: 3px;
}

QPushButton:hover {
    background-color: #4a4a4a;
    border: 1px solid #666666;
}

QPushButton:pressed {
    background-color: #2a2a2a;
}

QPushButton:disabled {
    background-color: #2a2a2a;
    color: #707070;
    border: 1px solid #404040;
}

QLineEdit {
    font-size: 11px;
    background-color: #2d2d2d;
    color: #e0e0e0;
    border: 1px solid #555555;
    border-radius: 4px;
    padding: 1px;
    selection-background-color: #448fff;
}

QLineEdit:focus {
    border: 1px solid #448fff;
}

QLineEdit:disabled {
    background-color: #252525;
    color: #707070;
    border: 1px solid #404040;
}

QComboBox {
    font-size: 11px;
    background-color: #3a3a3a;
    color: #e0e0e0;
    border: 1px solid #555555;
    border-radius: 4px;
    padding: 3px;
}

QComboBox::drop-down {
    border: none;
    width: 20px;
}

QComboBox::down-arrow {
    image: url(kqueue/icons/drop_down.svg);
    width: 12px;
    height: 12px;
}

QComboBox QAbstractItemView {
    background-color: #3a3a3a;
    color: #e0e0e0;
    border: 1px solid #404040;
    border-radius: 4px;
    selection-background-color: #555555;
    selection-color: #ffffff;
    outline: none;
}

QComboBox QAbstractItemView::item {
    padding: 4px;
    background-color: #2a2a2a;
    border: none;
}

QComboBox QAbstractItemView::item:hover {
    background-color: #2a2a2a;
}

QComboBox QAbstractItemView::item:selected {
    background-color: #3a3a3a;
    color: #ffffff;
}

QComboBox:disabled {
    background-color: #2a2a2a;
    color: #707070;
    border: 1px solid #404040;
}

QListWidget {
    color: #e0e0e0;
    border-radius: 6px;
    padding: 3px;
    font-size: 12px;
    border: 1px solid #555555;
    outline: none;
}

QListWidget::item {
    padding: 3px;
    border: 1px solid transparent;
    border-radius: 5px;
    margin: 0px;
}

QListWidget::item:hover {
    border: 1px solid #666666;
    outline: none;
}

QListWidget::item:selected {
    color: #ffffff;
    border: 1px solid #448fff;
    outline: none;
}

QListWidget::item:selected:active {
    color: #1e1e1e;
    background-color: #1e1e1e;
    border: 1px solid #3377dd;
    outline: none;
}

QScrollBar:vertical {
    background-color: transparent;
    width: 14px;
    border: none;
    margin: 0px;
    padding: 2px;
}

QScrollBar::handle:vertical {
    background-color: rgba(85, 85, 85, 120);
    border-radius: 5px;
    min-height: 20px;
    margin: 0px 0px;
}

QScrollBar::handle:vertical:hover {
    background-color: rgba(102, 102, 102, 180);
}

QScrollBar:vertical:hover {
    background-color: rgba(45, 45, 45, 30);
}

QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical {
    border: none;
    background: transparent;
    height: 0px;
}

QScrollBar::up-arrow:vertical,
QScrollBar::down-arrow:vertical,
QScrollBar::add-page:vertical,
QScrollBar::sub-page:vertical {
    background: transparent;
    border: none;
}

QScrollBar:horizontal {
    background-color: transparent;
    height: 14px;
    border: none;
    margin: 0px;
    padding: 2px;
}

QScrollBar::handle:horizontal {
    background-color: rgba(85, 85, 85, 120);
    border-radius: 5px;
    min-width: 20px;
    margin: 0px 0px;
}

QScrollBar::handle:horizontal:hover {
    background-color: rgba(102, 102, 102, 180);
}

QScrollBar:horizontal:hover {
    background-color: rgba(45, 45, 45, 30);
}

QScrollBar::add-line:horizontal,
QScrollBar::sub-line:horizontal {
    border: none;
    background: transparent;
    width: 0px;
}

QScrollBar::left-arrow:horizontal,
QScrollBar::right-arrow:horizontal,
QScrollBar::add-page:horizontal,
QScrollBar::sub-page:horizontal {
    background: transparent;
    border: none;
}

QMainWindow, QDialog, QWidget {
    background-color: #1e1e1e;
}

QMenuBar {
    background-color: #2d2d2d;
    color: #e0e0e0;
    font-size: 11px;
}

QMenuBar::item:selected {
    background-color: #448fff;
}

QMenu {
    background-color: #2d2d2d;
    color: #e0e0e0;
    border: 1px solid #555555;
    font-size: 11px;
}

QMenu::item:selected {
    background-color: #448fff;
}

QCheckBox, QRadioButton {
    color: #e0e0e0;
    font-size: 11px;
}

QCheckBox:disabled, QRadioButton:disabled {
    color: #707070;
    font-size: 11px;
}

QCheckBox::indicator, QRadioButton::indicator {
    width: 14px;
    height: 14px;
    border-radius: 4px;
}

QCheckBox::indicator:unchecked {
    background-color: #2d2d2d;
    border: 1px solid #555555;
}

QCheckBox::indicator:checked {
    background-color: #448fff;
    border: 1px solid #448fff;
}

QCheckBox::indicator:unchecked:disabled {
    background-color: #212121;
    border: 1px solid #2e2d2d;
}

QCheckBox::indicator:checked:disabled {
    background-color: #224880;
    border: 1px solid #224880;
}

QGroupBox {
    color: #e0e0e0;
    border: 1px solid #555555;
    border-radius: 5px;
    margin-top: 10px;
    font-size: 11px;
    font-weight: bold;
}

QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 5px 0 5px;
}

QTabWidget::pane {
    border: 1px solid #555555;
    background-color: #2d2d2d;
    border-radius: 4px;
}

QTabBar::tab {
    background-color: #3a3a3a;
    color: #e0e0e0;
    padding: 6px 12px;
    margin-right: 2px;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
    font-size: 11px;
}

QTabBar::tab:selected {
    background-color: #448fff;
    color: #ffffff;
}

QTabBar::tab:hover:!selected {
    background-color: #4a4a4a;
}

QTextEdit, QPlainTextEdit {
    background-color: #2d2d2d;
    color: #e0e0e0;
    border: 1px solid #555555;
    border-radius: 4px;
    padding: 3px;
    font-size: 11px;
    selection-background-color: #448fff;
}

QHeaderView::section {
    background-color: #3a3a3a;
    color: #e0e0e0;
    padding: 5px;
    border: 1px solid #555555;
    font-size: 11px;
}

QTableView, QTreeView {
    background-color: #2d2d2d;
    color: #e0e0e0;
    alternate-background-color: #252525;
    selection-background-color: #448fff;
    selection-color: #ffffff;
    font-size: 11px;
}

QTableView::item, QTreeView::item {
    padding: 3px;
}

QProgressBar {
    border: none;
    border-radius: 4px;
    background-color: #37474f;
    color: #e0e0e0;
    text-align: center;
    font-size: 11px;
    height: 4px;
}

QProgressBar::chunk {
    border-radius: 4px;
    background-color: #448fff;
    margin: 0px;
}

QToolTip {
    background-color: #3a3a3a;
    color: #e0e0e0;
    border: 1px solid #555555;
    border-radius: 4px;
    padding: 5px;
    font-size: 11px;
}
'''
