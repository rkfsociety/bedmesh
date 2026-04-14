import sys
import numpy as np
from PyQt6.QtWidgets import QMainWindow, QSplitter, QVBoxLayout, QWidget, QMessageBox
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

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(4, 4, 4, 4)

        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        layout.addWidget(self.splitter)

        self.left_panel = LeftPanel()
        self.mesh_view = MeshView()
        self.right_panel = RightPanel()

        self.splitter.addWidget(self.left_panel)
        self.splitter.addWidget(self.mesh_view)
        self.splitter.addWidget(self.right_panel)

        self.splitter.setStretchFactor(0, 1)
        self.splitter.setStretchFactor(1, 3)
        self.splitter.setStretchFactor(2, 1)

        self.left_panel.config_loaded.connect(self._handle_config_load)

    def _handle_config_load(self, filepath):
        try:
            data = self.parser.parse_file(filepath)
            if data:  # ← ИСПРАВЛЕНО
                self.mesh_view.update_mesh(data)
                stats = self._calculate_stats(data)
                self.right_panel.update_stats(stats)
                self.logger.info(f"✅ Mesh загружен: {data.x_count}x{data.y_count}")
            else:
                QMessageBox.warning(self, "Ошибка парсинга", "Не удалось найти данные bed_mesh в файле.")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось загрузить файл:\n{e}")

    def _calculate_stats(self, data) -> dict:
        z_flat = data.z.flatten()
        return {
            "min": float(np.min(z_flat)),
            "max": float(np.max(z_flat)),
            "mean": float(np.mean(z_flat)),
            "range": float(np.max(z_flat) - np.min(z_flat)),
            "count": len(z_flat),
            "z_flat": z_flat
        }

    def _restore_geometry(self):
        geo = self.config.get_window_geometry()
        if geo:
            self.restoreGeometry(geo)

    def closeEvent(self, event):
        self.config.save_window_geometry(self.saveGeometry())
        self.logger.info("🔒 Приложение закрыто")
        event.accept()