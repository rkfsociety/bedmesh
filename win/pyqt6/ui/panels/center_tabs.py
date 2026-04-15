from PyQt6.QtWidgets import QWidget, QVBoxLayout, QTabWidget, QTextEdit, QLabel, QPushButton, QHBoxLayout
from PyQt6.QtWidgets import QApplication
from ui.components.mesh_view import MeshView

class CenterTabs(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        # 🔹 Вкладка 1: Карта
        self.mesh_tab = QWidget()
        m_layout = QVBoxLayout(self.mesh_tab)
        m_layout.setContentsMargins(0, 0, 0, 0)
        
        btn_row = QHBoxLayout()
        btn_copy = QPushButton("📋 Копировать карту")
        btn_copy.setFixedSize(180, 28)
        btn_copy.clicked.connect(self._on_copy_mesh)
        btn_row.addWidget(btn_copy)
        btn_row.addStretch()
        m_layout.addLayout(btn_row)
        
        self.mesh_view = MeshView()
        m_layout.addWidget(self.mesh_view)
        self.tabs.addTab(self.mesh_tab, "📊 Карта стола")

        # Вкладка 2: Настройка
        self.settings_tab = QWidget()
        s_layout = QVBoxLayout(self.settings_tab)
        s_layout.addWidget(QLabel("🔧 Настройка параметров принтера (в разработке)"))
        self.tabs.addTab(self.settings_tab, "⚙️ Настройка")

        self.raw_tab = QWidget()
        r_layout = QVBoxLayout(self.raw_tab)
        r_layout.setContentsMargins(5, 5, 5, 5)
        self.raw_text = QTextEdit()
        self.raw_text.setReadOnly(True)
        self.raw_text.setStyleSheet("font-family: Consolas, monospace; font-size: 12px; background: #1e1e1e; color: #d4d4d4;")
        r_layout.addWidget(self.raw_text)
        self.tabs.addTab(self.raw_tab, "📄 Printer Mutable")

    def _on_copy_mesh(self):
        self.mesh_view.copy_to_clipboard()
