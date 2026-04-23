from PyQt6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QPushButton,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ui.components.config_editor import ConfigEditor
from ui.components.mesh_view import MeshView
from utils.strings import S


class CenterTabs(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)
        self._advanced_visible = True

        self.mesh_tab = QWidget()
        mesh_layout = QVBoxLayout(self.mesh_tab)
        mesh_layout.setContentsMargins(0, 0, 0, 0)

        button_row = QHBoxLayout()
        btn_copy = QPushButton(S.get("mesh.copy_btn"))
        btn_copy.setFixedSize(180, 28)
        btn_copy.clicked.connect(self._on_copy_mesh)
        button_row.addWidget(btn_copy)
        button_row.addStretch()
        mesh_layout.addLayout(button_row)

        self.mesh_view = MeshView()
        mesh_layout.addWidget(self.mesh_view)
        self.tabs.addTab(self.mesh_tab, S.get("mesh.tab_title"))

        self.config_tab = QWidget()
        config_layout = QVBoxLayout(self.config_tab)
        config_layout.setContentsMargins(0, 0, 0, 0)
        self.config_editor = ConfigEditor()
        config_layout.addWidget(self.config_editor)
        self.tabs.addTab(self.config_tab, S.get("config.tab_title"))

        self.raw_tab = QWidget()
        raw_layout = QVBoxLayout(self.raw_tab)
        raw_layout.setContentsMargins(5, 5, 5, 5)
        self.raw_text = QTextEdit()
        self.raw_text.setReadOnly(True)
        self.raw_text.setStyleSheet(
            "font-family: Consolas, monospace; font-size: 12px; background: #1e1e1e; color: #d4d4d4;"
        )
        raw_layout.addWidget(self.raw_text)
        self.tabs.addTab(self.raw_tab, S.get("raw.tab_title"))

        self.set_advanced_visible(False)

    def set_advanced_visible(self, visible: bool):
        visible = bool(visible)
        if visible == self._advanced_visible:
            return
        self._advanced_visible = visible

        def _tab_index(widget: QWidget) -> int:
            try:
                return self.tabs.indexOf(widget)
            except Exception:
                return -1

        if not visible:
            current_widget = self.tabs.currentWidget()
            if current_widget in (self.config_tab, self.raw_tab):
                self.tabs.setCurrentWidget(self.mesh_tab)

            raw_index = _tab_index(self.raw_tab)
            if raw_index >= 0:
                self.tabs.removeTab(raw_index)

            config_index = _tab_index(self.config_tab)
            if config_index >= 0:
                self.tabs.removeTab(config_index)
            return

        if _tab_index(self.config_tab) < 0:
            self.tabs.insertTab(1, self.config_tab, S.get("config.tab_title"))
        if _tab_index(self.raw_tab) < 0:
            self.tabs.insertTab(2, self.raw_tab, S.get("raw.tab_title"))

    def _on_copy_mesh(self):
        self.mesh_view.copy_to_clipboard()
