import sys
import numpy as np
import os
from PyQt6.QtWidgets import QMainWindow, QSplitter, QVBoxLayout, QWidget, QMessageBox
from PyQt6.QtCore import Qt

from ui.panels.left_panel import LeftPanel
from ui.panels.right_panel import RightPanel
from ui.components.mesh_view import MeshView
from core.mesh_parser import MeshParser, BedMeshData
from core.ssh_client import download_cfg_via_ssh
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

        self.left_panel.file_selected.connect(self._handle_file_load)
        self.left_panel.ssh_requested.connect(self._handle_ssh_load)

    def _handle_file_load(self, filepath):
        self._process_file(filepath)

    def _handle_ssh_load(self, ip_address):
        try:
            self.logger.info(f"Подключение к {ip_address}...")
            temp_path = download_cfg_via_ssh(ip_address)
            
            if temp_path:
                self._process_file(temp_path)
            else:
                QMessageBox.critical(self, "Ошибка SSH", "Не удалось подключиться к принтеру.")
        finally:
            self.left_panel.btn_ssh.setEnabled(True)
            self.left_panel.btn_ssh.setText("🌐 Загрузить по SSH")

    def _process_file(self, filepath):
        try:
            data = self.parser.parse_file(filepath)
            if data:  # ← ИСПРАВЛЕНО: было обрезано до "if "
                self.mesh_view.update_mesh(data)
                stats = self._calculate_advanced_stats(data)
                self.right_panel.update_all(stats)
                self.logger.info(f"✅ Mesh загружен: {data.x_count}x{data.y_count}")
            else:
                QMessageBox.warning(self, "Ошибка", "В файле нет данных bed_mesh.")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось обработать файл:\n{e}")

    def _calculate_advanced_stats(self, data: BedMeshData) -> dict:
        z_flat = data.z.flatten()
        
        min_val = float(np.min(z_flat))
        max_val = float(np.max(z_flat))
        mean_val = float(np.mean(z_flat))
        range_val = float(max_val - min_val)
        var_val = float(np.var(z_flat))
        rms_val = float(np.sqrt(np.mean(z_flat**2)))

        fl_val = float(data.z[0, 0])
        fr_val = float(data.z[0, -1])
        center_x_idx = data.x_count // 2
        bc_val = float(data.z[-1, center_x_idx])

        fl_corr = fl_val - mean_val
        fr_corr = fr_val - mean_val
        bc_corr = bc_val - mean_val

        return {
            "min": min_val, "max": max_val, "range": range_val,
            "mean": mean_val, "var": var_val, "rms": rms_val,
            "front_left": fl_corr, "front_right": fr_corr, "back_center": bc_corr
        }

    def _restore_geometry(self):
        geo = self.config.get_window_geometry()
        if geo:
            self.restoreGeometry(geo)

    def closeEvent(self, event):
        self.config.save_window_geometry(self.saveGeometry())
        self.logger.info("🔒 Приложение закрыто")
        event.accept()