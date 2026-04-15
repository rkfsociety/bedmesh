import sys
import numpy as np
import os
import traceback
from PyQt6.QtWidgets import QMainWindow, QSplitter, QVBoxLayout, QWidget, QMessageBox
from PyQt6.QtCore import Qt

from ui.panels.left_panel import LeftPanel
from ui.panels.right_panel import RightPanel
from ui.panels.center_tabs import CenterTabs
from core.mesh_parser import MeshParser, BedMeshData
from core.ssh_client import download_cfg_via_ssh
from utils.logger import get_logger
from utils.app_config import AppConfig
from utils.strings import S

class BedMeshApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.logger = get_logger(__name__)
        self.config = AppConfig()
        self.parser = MeshParser()
        self.settings = self.config.load()
        self._last_ssh_data = None

        self._init_ui()
        self._restore_geometry()
        self.logger.info("✅ Приложение инициализировано")

    def _init_ui(self):
        self.setWindowTitle(S.get("app.title"))
        self.resize(1280, 800)

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(4, 4, 4, 4)

        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        layout.addWidget(self.splitter)

        self.left_panel = LeftPanel(self.settings)
        self.center_tabs = CenterTabs()
        self.right_panel = RightPanel()

        self.splitter.addWidget(self.left_panel)
        self.splitter.addWidget(self.center_tabs)
        self.splitter.addWidget(self.right_panel)

        self.splitter.setStretchFactor(0, 1)
        self.splitter.setStretchFactor(1, 3)
        self.splitter.setStretchFactor(2, 1)

        # --- Коннекты ---
        self.left_panel.file_selected.connect(self._handle_file_load)
        
        # SSH загрузка через ConfigEditor
        self.left_panel.ssh_download_requested.connect(self._handle_ssh_load_via_editor)
        
        # Сброс кнопки в левой панели после завершения операции в редакторе
        self.center_tabs.config_editor.ssh_operation_finished.connect(self.left_panel.reset_ssh_button)
        # После успешной SSH-загрузки — обновляем RAW и пробуем построить карту
        self.center_tabs.config_editor.ssh_download_succeeded.connect(self._handle_ssh_file_downloaded)
        
        self.left_panel.setting_updated.connect(self._on_setting_changed)

    def _on_setting_changed(self, key: str, value: str):
        self.settings[key] = value
        self.config.save()

    def _handle_file_load(self, filepath):
        self._process_file(filepath)

    def _handle_ssh_load_via_editor(self, ssh_data):
        """Передает управление загрузкой по SSH в ConfigEditor"""
        try:
            self._last_ssh_data = ssh_data
            # Пользователи ожидают результат именно в редакторе конфига/RAW, поэтому
            # при SSH-загрузке сразу показываем вкладку редактора.
            self.center_tabs.tabs.setCurrentWidget(self.center_tabs.config_tab)
            self.center_tabs.config_editor.load_from_ssh_data(ssh_data)
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось инициировать загрузку:\n{str(e)}")
            self.left_panel.reset_ssh_button()

    def _handle_ssh_file_downloaded(self, local_path: str):
        # После SSH-загрузки пробуем построить карту.
        # Важно: не переключаем вкладки "вслепую", иначе можно перебить переход на вкладку карты.
        try:
            has_mesh = self._process_file(local_path)
            if not has_mesh:
                self.center_tabs.tabs.setCurrentWidget(self.center_tabs.raw_tab)
        except Exception as e:
            self.logger.exception("SSH file post-process failed: %s", e)

    def _process_file(self, filepath):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                raw_content = f.read()
            self.center_tabs.raw_text.setPlainText(raw_content)

            data = self.parser.parse_file(filepath)

            if data:
                self.center_tabs.mesh_view.update_mesh(data)
                stats = self._calculate_advanced_stats(data)
                self.right_panel.update_all(stats)
                self.logger.info(f"✅ Mesh загружен: {data.x_count}x{data.y_count}")
                self.center_tabs.tabs.setCurrentWidget(self.center_tabs.mesh_tab)
                return True
            else:
                # printer.cfg часто содержит только настройки bed_mesh, а сохранённые points лежат в printer_mutable.cfg.
                mutable_path = "/userdata/app/gk/printer_mutable.cfg"
                if self._last_ssh_data and os.path.basename(filepath) in ("download_printer.cfg", "temp_download.cfg", "printer.cfg"):
                    ip = self._last_ssh_data.get("ip")
                    port = int(self._last_ssh_data.get("port", 2222))
                    user = self._last_ssh_data.get("user", "root")
                    pwd = self._last_ssh_data.get("password", "")
                    self.logger.info("No mesh points in %s, trying SSH download: %s", filepath, mutable_path)
                    alt_local = download_cfg_via_ssh(ip, port, user, pwd, mutable_path)
                    if alt_local:
                        alt_data = self.parser.parse_file(alt_local)
                        if alt_data:
                            self.center_tabs.mesh_view.update_mesh(alt_data)
                            stats = self._calculate_advanced_stats(alt_data)
                            self.right_panel.update_all(stats)
                            self.center_tabs.tabs.setCurrentWidget(self.center_tabs.mesh_tab)
                            self.logger.info("✅ Mesh загружен из printer_mutable.cfg: %sx%s", alt_data.x_count, alt_data.y_count)
                            return True
                QMessageBox.warning(self, "Ошибка", S.get("app.msg_no_mesh"))
                return False
        except Exception as e:
            error_msg = S.get("app.msg_process_error", error=e, traceback=traceback.format_exc())
            self.logger.error(error_msg)
            QMessageBox.critical(self, "Ошибка", error_msg)
            return False

    def _calculate_advanced_stats(self, data):
        z_flat = data.z.flatten()
        min_val, max_val = float(np.min(z_flat)), float(np.max(z_flat))
        mean_val = float(np.mean(z_flat))
        return {
            "min": min_val, "max": max_val, "range": float(max_val - min_val),
            "mean": mean_val, "var": float(np.var(z_flat)), "rms": float(np.sqrt(np.mean(z_flat**2))),
            "front_left": float(data.z[0, 0] - mean_val),
            "front_right": float(data.z[0, -1] - mean_val),
            "back_center": float(data.z[-1, data.x_count // 2] - mean_val)
        }

    def _restore_geometry(self):
        geo = self.config.get_window_geometry()
        if geo:
            self.restoreGeometry(geo)

    def closeEvent(self, event):
        self.config.save_window_geometry(self.saveGeometry())
        self.logger.info("🔒 Приложение закрыто")
        event.accept()