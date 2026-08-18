"""Единая тема Windows-интерфейса Bed Mesh Visualizer."""

from PyQt6.QtWidgets import QApplication


APP_STYLESHEET = """
QMainWindow, QWidget {
    background: #0f1728;
    color: #e8eef8;
    font-family: "Segoe UI";
    font-size: 12px;
}
QMainWindow { background: #0b1220; }
QLabel { background: transparent; }
QSplitter::handle {
    background: #1d2a42;
    width: 5px;
}
QSplitter::handle:hover { background: #4f78b8; }
QTabWidget::pane {
    background: #111b2e;
    border: 1px solid #263956;
    border-radius: 7px;
    top: -1px;
}
QTabBar::tab {
    background: #17233a;
    color: #96a7c2;
    border: 1px solid #263956;
    border-bottom: none;
    border-top-left-radius: 7px;
    border-top-right-radius: 7px;
    padding: 8px 14px;
    margin-right: 3px;
}
QTabBar::tab:hover { color: #e8eef8; background: #1e3151; }
QTabBar::tab:selected {
    color: #f5f8ff;
    background: #24395d;
    border-color: #4d78b5;
}
QPushButton {
    background: #1a2942;
    color: #e8eef8;
    border: 1px solid #314968;
    border-radius: 6px;
    padding: 6px 11px;
    min-height: 25px;
}
QPushButton:hover { background: #263e63; border-color: #5c88c7; }
QPushButton:pressed { background: #15243c; }
QPushButton:disabled { color: #65748c; background: #141e31; border-color: #25334a; }
QPushButton#primaryButton {
    background: #376ac0;
    border-color: #6290dc;
    color: white;
    font-weight: 600;
}
QPushButton#primaryButton:hover { background: #477bd4; }
QLineEdit, QComboBox, QListWidget, QTextEdit {
    background: #101a2b;
    color: #e8eef8;
    border: 1px solid #304765;
    border-radius: 5px;
    padding: 5px 7px;
    selection-background-color: #3565aa;
}
QLineEdit:focus, QComboBox:focus, QTextEdit:focus { border-color: #5b8bd0; }
QComboBox QAbstractItemView {
    background: #14223a;
    color: #e8eef8;
    border: 1px solid #3c5b84;
    selection-background-color: #2d5591;
}
QGroupBox {
    background: #131f34;
    border: 1px solid #2a3d5b;
    border-radius: 7px;
    margin-top: 10px;
    padding: 12px 8px 8px 8px;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 9px;
    padding: 0 6px;
    color: #b9c9e0;
    background: #131f34;
}
QScrollArea { background: #0f1728; border: none; }
QScrollBar:vertical {
    background: #101a2b;
    width: 11px;
    margin: 2px;
    border-radius: 5px;
}
QScrollBar::handle:vertical { background: #344d70; min-height: 35px; border-radius: 5px; }
QScrollBar::handle:vertical:hover { background: #4e70a0; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QToolTip { background: #1e3150; color: #f3f7ff; border: 1px solid #5a7eaf; padding: 5px; }
"""


def apply_app_theme(app: QApplication) -> None:
    app.setStyleSheet(APP_STYLESHEET)
