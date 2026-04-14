from PyQt6.QtWidgets import QWidget, QVBoxLayout, QTabWidget, QTextEdit, QLabel
from ui.components.mesh_view import MeshView

class CenterTabs(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        # Вкладка 1: Карта
        self.mesh_tab = QWidget()
        m_layout = QVBoxLayout(self.mesh_tab)
        m_layout.setContentsMargins(0, 0, 0, 0)
        self.mesh_view = MeshView()
        m_layout.addWidget(self.mesh_view)
        self.tabs.addTab(self.mesh_tab, "📊 Карта стола")

        # Вкладка 2: Настройка принтера
        self.settings_tab = QWidget()
        s_layout = QVBoxLayout(self.settings_tab)
        s_layout.addWidget(QLabel("🔧 Настройка параметров принтера (в разработке)"))
        self.tabs.addTab(self.settings_tab, "⚙️ Настройка")

        # Вкладка 3: Сырой CFG
        self.raw_tab = QWidget()
        r_layout = QVBoxLayout(self.raw_tab)
        r_layout.setContentsMargins(5, 5, 5, 5)
        self.raw_text = QTextEdit()
        self.raw_text.setReadOnly(True)
        self.raw_text.setStyleSheet("font-family: Consolas, monospace; font-size: 12px; background: #1e1e1e; color: #d4d4d4;")
        r_layout.addWidget(self.raw_text)
        self.tabs.addTab(self.raw_tab, "📄 Сырой CFG")