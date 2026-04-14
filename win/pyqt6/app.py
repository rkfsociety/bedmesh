import sys
from PyQt6.QtWidgets import QMainWindow, QSplitter, QVBoxLayout, QWidget
from PyQt6.QtCore import Qt

from ui.panels.left_panel import LeftPanel
from ui.panels.right_panel import RightPanel
from ui.components.mesh_view import MeshView
from core.mesh_parser import MeshParser
from utils.logger import get_logger
from utils.app_config import AppConfig

class BedMeshApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.logger = get_logger(__name__)
        self.config = AppConfig()
        self.parser = MeshParser()

        self._init_ui()
        self._restore_geometry()
        self.logger.info("✅ Приложение инициализировано")

    def _init_ui(self):
        self.setWindowTitle("BedMesh Visualizer")
        self.resize(1280, 800)

        # Центральный контейнер
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(4, 4, 4, 4)

        # Основной сплиттер (Лево / Центр / Право)
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        layout.addWidget(self.splitter)

        # Панели
        self.left_panel = LeftPanel()
        self.mesh_view = MeshView()
        self.right_panel = RightPanel()

        self.splitter.addWidget(self.left_panel)
        self.splitter.addWidget(self.mesh_view)
        self.splitter.addWidget(self.right_panel)

        # Пропорции: 1 : 3 : 1
        self.splitter.setStretchFactor(0, 1)
        self.splitter.setStretchFactor(1, 3)
        self.splitter.setStretchFactor(2, 1)

    def _restore_geometry(self):
        geo = self.config.get_window_geometry()
        if geo:
            self.restoreGeometry(geo)

    def closeEvent(self, event):
        self.config.save_window_geometry(self.saveGeometry())
        self.logger.info("🔒 Приложение закрыто")
        event.accept()