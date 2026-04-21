from PyQt6.QtWidgets import QWidget, QVBoxLayout, QTabWidget, QTextEdit, QLabel, QPushButton, QHBoxLayout
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QPixmap
from ui.components.mesh_view import MeshView
from ui.components.config_editor import ConfigEditor
from utils.strings import S

class CenterTabs(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)
        self._advanced_visible = True

        # 🔹 Вкладка 1: Карта
        self.mesh_tab = QWidget()
        m_layout = QVBoxLayout(self.mesh_tab)
        m_layout.setContentsMargins(0, 0, 0, 0)
        
        btn_row = QHBoxLayout()
        btn_copy = QPushButton(S.get("mesh.copy_btn"))
        btn_copy.setFixedSize(180, 28)
        btn_copy.clicked.connect(self._on_copy_mesh)
        btn_row.addWidget(btn_copy)
        btn_row.addStretch()
        m_layout.addLayout(btn_row)
        
        self.mesh_view = MeshView()
        m_layout.addWidget(self.mesh_view)
        self.tabs.addTab(self.mesh_tab, S.get("mesh.tab_title"))

        # 🔹 Вкладка 2: Редактор конфига
        self.config_tab = QWidget()
        c_layout = QVBoxLayout(self.config_tab)
        c_layout.setContentsMargins(0, 0, 0, 0)
        self.config_editor = ConfigEditor()
        c_layout.addWidget(self.config_editor)
        self.tabs.addTab(self.config_tab, S.get("config.tab_title"))

        # 🔹 Вкладка 3: Сырой CFG
        self.raw_tab = QWidget()
        r_layout = QVBoxLayout(self.raw_tab)
        r_layout.setContentsMargins(5, 5, 5, 5)
        self.raw_text = QTextEdit()
        self.raw_text.setReadOnly(True)
        self.raw_text.setStyleSheet("font-family: Consolas, monospace; font-size: 12px; background: #1e1e1e; color: #d4d4d4;")
        r_layout.addWidget(self.raw_text)
        self.tabs.addTab(self.raw_tab, S.get("raw.tab_title"))

        # Default: hide advanced tabs until user enables them.
        self.set_advanced_visible(False)

    def set_advanced_visible(self, visible: bool):
        """
        Show/hide advanced tabs:
        - Настройки Принтера
        - Printer Mutable
        """
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
            # If currently on an advanced tab, jump back to mesh.
            cur = self.tabs.currentWidget()
            if cur in (self.config_tab, self.raw_tab):
                self.tabs.setCurrentWidget(self.mesh_tab)

            # Remove in reverse order to keep indices stable.
            idx_raw = _tab_index(self.raw_tab)
            if idx_raw >= 0:
                self.tabs.removeTab(idx_raw)
            idx_cfg = _tab_index(self.config_tab)
            if idx_cfg >= 0:
                self.tabs.removeTab(idx_cfg)
            return

        # Show: insert after mesh tab in a fixed order.
        if _tab_index(self.config_tab) < 0:
            self.tabs.insertTab(1, self.config_tab, S.get("config.tab_title"))
        if _tab_index(self.raw_tab) < 0:
            self.tabs.insertTab(2, self.raw_tab, S.get("raw.tab_title"))

    def _on_copy_mesh(self):
        self.mesh_view.copy_to_clipboard()