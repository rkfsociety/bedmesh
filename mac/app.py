import os
import traceback

import numpy as np
from PyQt6.QtCore import Qt, pyqtSignal, QObject, QThread
from PyQt6.QtWidgets import QMessageBox, QMainWindow, QSplitter, QVBoxLayout, QWidget

from core.mesh_parser import MeshParser
from core.ssh_client import (
    download_cfg_via_ssh,
    get_ssh_connection,
    send_gcode_via_temporary_bridge,
    BED_MESH_CALIBRATION_COMMANDS,
    BED_MESH_COOLDOWN_COMMANDS,
    get_bed_mesh_grid,
    read_remote_text_via_ssh,
    save_live_mesh_to_mutable,
)
from core.live_mesh import LiveMeshAccumulator
from ui.panels.center_tabs import CenterTabs
from ui.panels.left_panel import LeftPanel
from ui.panels.right_panel import RightPanel
from utils import updater
from utils.app_config import AppConfig
from utils.logger import get_logger
from utils.strings import S
from utils.version import VERSION


class _CalibrationWorker(QObject):
    snapshot = pyqtSignal(object)
    status = pyqtSignal(str)
    finished = pyqtSignal(bool, str)

    def __init__(self, ssh_data: dict):
        super().__init__()
        self.ssh_data = ssh_data

    def run(self):
        import time

        monitor = stdout = None
        accumulator = LiveMeshAccumulator()
        ip = self.ssh_data.get("ip", "")
        port = int(self.ssh_data.get("port", 2222))
        user = self.ssh_data.get("user", "root")
        password = self.ssh_data.get("password", "")
        try:
            self.status.emit("Подключено. Читаю настройки сетки из printer.cfg...")
            grid = get_bed_mesh_grid(ip, port, user, password)
            if grid is None:
                self.finished.emit(False, "Не удалось прочитать [bed_mesh] из printer.cfg.")
                return
            accumulator = LiveMeshAccumulator(
                total_points=grid["total_points"],
                x=np.linspace(grid["min_x"], grid["max_x"], grid["x_count"]),
                y=np.linspace(grid["min_y"], grid["max_y"], grid["y_count"]),
            )
            monitor = get_ssh_connection(ip, port, user, password)
            _, stdout, _ = monitor.exec_command("tail -n 0 -F /tmp/gklib.log")
            stdout.channel.settimeout(1.0)
            for command in BED_MESH_CALIBRATION_COMMANDS:
                self.status.emit({
                    "LEVIQ2_PREHEATING": "Прогрев стола и сопла...",
                    "LEVIQ2_WIPING": "Очистка сопла...",
                    "G28 Z": "Хоуминг оси Z...",
                    "LEVIQ2_PROBE": "Запуск измерений тензодатчиком...",
                }.get(command, f"Отправка команды {command}..."))
                ok, details = send_gcode_via_temporary_bridge(ip, port, user, password, command)
                if not ok:
                    self.finished.emit(False, f"Не удалось отправить штатную команду {command} по SSH.\n{details}")
                    return

            first_point_deadline = time.monotonic() + 180
            idle_timeout = 20
            idle_since = time.monotonic()
            while True:
                now = time.monotonic()
                try:
                    line = stdout.readline()
                except Exception:
                    line = ""
                if line and accumulator.feed_line(line):
                    idle_since = time.monotonic()
                    point = accumulator.current
                    self.status.emit(
                        f"Измерение точки {len(accumulator.points)}/{accumulator.total_points}: "
                        f"X={point[0]:.1f} Y={point[1]:.1f}"
                    )
                    self.snapshot.emit(accumulator.snapshot())
                else:
                    time.sleep(0.15)
                if accumulator.points and now - idle_since >= idle_timeout:
                    break
                if not accumulator.points and now >= first_point_deadline:
                    self.finished.emit(False, "Принтер не передал ни одной точки за 3 минуты. Проверьте журнал принтера.")
                    return

            self.status.emit("Карта снята. Отключаю нагрев стола и сопла...")
            for command in BED_MESH_COOLDOWN_COMMANDS:
                ok, _ = send_gcode_via_temporary_bridge(ip, port, user, password, command)
                if not ok:
                    self.status.emit(f"Предупреждение: не удалось отправить {command}")
            snapshot = accumulator.snapshot()
            if snapshot is None or snapshot.measured_points != snapshot.total_points:
                self.finished.emit(False, f"Получено только {snapshot.measured_points if snapshot else 0} "
                                          f"из {snapshot.total_points if snapshot else grid['total_points']} точек. "
                                          "Неполная карта не сохранена.")
                return

            self.status.emit("Сохраняю карту на принтер...")
            saved, details = save_live_mesh_to_mutable(snapshot.data, ip, port, user, password)
            if not saved:
                self.finished.emit(False, f"Карта снята, но не сохранена: {details}")
                return
            self.finished.emit(True, f"Получено и сохранено точек: {snapshot.measured_points}. Новая карта записана в printer_mutable.cfg.")
        except Exception as error:
            self.finished.emit(False, str(error))
        finally:
            if stdout is not None:
                stdout.channel.close()
            if monitor is not None:
                monitor.close()
class BedMeshApp(QMainWindow):
    _update_check_done = pyqtSignal(str, object, object)

    def __init__(self):
        super().__init__()
        try:
            from PyQt6.QtWidgets import QApplication

            self.setWindowIcon(QApplication.instance().windowIcon())
        except Exception:
            pass
        self.logger = get_logger(__name__)
        self.config = AppConfig()
        self.parser = MeshParser()
        self.settings = self.config.load()
        self._last_ssh_data = None
        self._last_mesh_data = None

        self._init_ui()
        self._restore_geometry()
        self.logger.info("✅ Приложение инициализировано")

        self.right_panel.clear_update_available(f"v{VERSION}")
        self.right_panel.set_update_handler(self._on_update_button_clicked)
        self._update_release_data = None
        self._update_check_done.connect(self._apply_update_check_result)
        self._check_updates_quiet()

    def _init_ui(self):
        self.setWindowTitle(f"{S.get('app.title')} v{VERSION}")
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

        self.center_tabs.set_mesh_palette(self.settings.get("mesh_palette", "soft"))
        self.center_tabs.view_mode_changed.connect(self._on_view_mode_changed)

        self.splitter.addWidget(self.left_panel)
        self.splitter.addWidget(self.center_tabs)
        self.splitter.addWidget(self.right_panel)

        self.splitter.setStretchFactor(0, 1)
        self.splitter.setStretchFactor(1, 3)
        self.splitter.setStretchFactor(2, 1)

        self.left_panel.ssh_download_requested.connect(self._handle_ssh_load_via_editor)
        self.left_panel.calibration_requested.connect(self._start_calibration)
        self.center_tabs.config_editor.ssh_operation_finished.connect(self.left_panel.reset_ssh_button)
        self.center_tabs.config_editor.ssh_download_succeeded.connect(self._handle_ssh_file_downloaded)

        self.left_panel.setting_updated.connect(self._on_setting_changed)
        self.left_panel.advanced_toggled.connect(self.center_tabs.set_advanced_visible)

        saved_mode = self.settings.get("mesh_view_mode", "2d")
        if saved_mode == "3d":
            self.center_tabs.set_view_mode("3d")

    def _check_updates_quiet(self):
        self.right_panel.set_checking_updates(True)

        def on_result(status: str, latest_tag: str | None, data: dict | None):
            self._update_check_done.emit(status, latest_tag, data)

        updater.check_for_updates_detailed(VERSION, on_result)

    def _apply_update_check_result(self, status: str, latest_tag_obj: object, data_obj: object):
        latest_tag = latest_tag_obj if isinstance(latest_tag_obj, str) else None
        data = data_obj if isinstance(data_obj, dict) else None

        self.right_panel.set_checking_updates(False)
        if status == "update" and data:
            self._update_release_data = data
            self.right_panel.set_update_available(data, latest_tag=latest_tag, current_version=VERSION)
        elif status == "none":
            self._update_release_data = None
            self.right_panel.clear_update_available(f"v{VERSION}")
        else:
            if self._update_release_data:
                self.right_panel.set_update_available(self._update_release_data)
            else:
                self.right_panel.clear_update_available(f"v{VERSION}")

    def _on_update_button_clicked(self, release_data: dict | None):
        if release_data:
            updater.install_update(release_data, parent=self)
        else:
            self._check_updates_quiet()

    def _on_setting_changed(self, key: str, value: str):
        self.settings[key] = value
        self.config.save()

    def _on_view_mode_changed(self, mode: str):
        self.settings["mesh_view_mode"] = mode
        self.config.save()

    def _handle_ssh_load_via_editor(self, ssh_data):
        try:
            self._last_ssh_data = ssh_data
            self.center_tabs.nozzle_tab.set_ssh_config(ssh_data)
            self.center_tabs.config_editor.load_from_ssh_data(ssh_data)
        except Exception as error:
            QMessageBox.critical(self, "Ошибка", f"Не удалось инициировать загрузку:\n{error}")
            self.left_panel.reset_ssh_button()

    def _start_calibration(self, ssh_data: dict):
        if getattr(self, "_calibration_thread", None) and self._calibration_thread.isRunning():
            return
        self._calibration_thread = QThread(self)
        self._calibration_worker = _CalibrationWorker(ssh_data)
        self._calibration_worker.moveToThread(self._calibration_thread)
        self._calibration_thread.started.connect(self._calibration_worker.run)
        self._calibration_worker.snapshot.connect(self._on_live_mesh_snapshot)
        self._calibration_worker.status.connect(self.left_panel.set_calibration_status)
        self._calibration_worker.finished.connect(self._on_calibration_finished)
        self._calibration_worker.finished.connect(self._calibration_thread.quit)
        self._calibration_worker.finished.connect(self._calibration_worker.deleteLater)
        self._calibration_thread.finished.connect(self._calibration_thread.deleteLater)
        self._calibration_thread.start()

    def _on_live_mesh_snapshot(self, snapshot):
        if snapshot is None:
            return
        self._last_mesh_data = snapshot.data
        self.center_tabs.update_mesh_views(snapshot.data)
        self.center_tabs.tabs.setCurrentWidget(self.center_tabs.mesh_tab)
        self.right_panel.update_all(self._calculate_advanced_stats(snapshot.data))

    def _on_calibration_finished(self, ok: bool, message: str):
        self._calibration_worker = None
        self._calibration_thread = None
        self.left_panel.calibration_finished(ok, message)

    def _handle_ssh_file_downloaded(self, local_path: str):
        try:
            self.center_tabs.nozzle_tab.load_file(local_path)
            if self._last_ssh_data:
                ip = self._last_ssh_data.get("ip", "")
                port = int(self._last_ssh_data.get("port", 2222))
                user = self._last_ssh_data.get("user", "root")
                password = self._last_ssh_data.get("password", "")
                metadata = read_remote_text_via_ssh(
                    ip, port, user, password, "/userdata/app/gk/config/nozzle.cfg"
                )
                mutable = read_remote_text_via_ssh(
                    ip, port, user, password, "/userdata/app/gk/printer_mutable.cfg"
                )
                if metadata:
                    self.center_tabs.nozzle_tab.load_metadata(metadata)
                if mutable:
                    self.center_tabs.nozzle_tab.load_mutable(mutable)
            has_mesh = self._process_file(local_path)
            if not has_mesh:
                self.center_tabs.tabs.setCurrentWidget(self.center_tabs.raw_tab)
        except Exception as error:
            self.logger.exception("SSH file post-process failed: %s", error)

    def _process_file(self, filepath):
        try:
            with open(filepath, "r", encoding="utf-8") as file_obj:
                raw_content = file_obj.read()
            self.center_tabs.raw_text.setPlainText(raw_content)

            data = self.parser.parse_file(filepath)

            if data:
                self._last_mesh_data = data
                self.center_tabs.update_mesh_views(data)
                stats = self._calculate_advanced_stats(data)
                self.right_panel.update_all(stats)
                self.right_panel.update_shaper(self.parser.parse_input_shaper_text(raw_content))
                self.logger.info("✅ Mesh загружен: %sx%s", data.x_count, data.y_count)
                self.center_tabs.tabs.setCurrentWidget(self.center_tabs.mesh_tab)
                return True

            mutable_path = "/userdata/app/gk/printer_mutable.cfg"
            if self._last_ssh_data and os.path.basename(filepath) in ("download_printer.cfg", "temp_download.cfg", "printer.cfg"):
                ip = self._last_ssh_data.get("ip")
                port = int(self._last_ssh_data.get("port", 2222))
                user = self._last_ssh_data.get("user", "root")
                pwd = self._last_ssh_data.get("password", "")
                self.logger.info("No mesh points in %s, trying SSH download: %s", filepath, mutable_path)
                alt_local = download_cfg_via_ssh(ip, port, user, pwd, mutable_path)
                if alt_local:
                    try:
                        with open(alt_local, "r", encoding="utf-8") as file_obj:
                            self.center_tabs.raw_text.setPlainText(file_obj.read())
                    except Exception:
                        self.logger.exception("Failed to update RAW from %s", alt_local)
                    alt_data = self.parser.parse_file(alt_local)
                    if alt_data:
                        self._last_mesh_data = alt_data
                        self.center_tabs.update_mesh_views(alt_data)
                        stats = self._calculate_advanced_stats(alt_data)
                        self.right_panel.update_all(stats)
                        alt_shaper = self.parser.parse_input_shaper_text(alt_content)
                        self.right_panel.update_shaper(
                            alt_shaper or self.parser.parse_input_shaper_text(raw_content)
                        )
                        self.center_tabs.tabs.setCurrentWidget(self.center_tabs.mesh_tab)
                        self.logger.info("✅ Mesh загружен из printer_mutable.cfg: %sx%s", alt_data.x_count, alt_data.y_count)
                        return True

            QMessageBox.warning(self, "Ошибка", S.get("app.msg_no_mesh"))
            return False
        except Exception as error:
            error_msg = S.get("app.msg_process_error", error=error, traceback=traceback.format_exc())
            self.logger.error(error_msg)
            QMessageBox.critical(self, "Ошибка", error_msg)
            return False

    def _calculate_advanced_stats(self, data):
        z_flat = data.z.flatten()
        min_val, max_val = float(np.min(z_flat)), float(np.max(z_flat))
        mean_val = float(np.mean(z_flat))
        return {
            "min": min_val,
            "max": max_val,
            "range": float(max_val - min_val),
            "mean": mean_val,
            "var": float(np.var(z_flat)),
            "rms": float(np.sqrt(np.mean(z_flat**2))),
            "front_left": float(data.z[0, 0] - mean_val),
            "front_right": float(data.z[0, -1] - mean_val),
            "back_center": float(data.z[-1, data.x_count // 2] - mean_val),
        }

    def _restore_geometry(self):
        geo = self.config.get_window_geometry()
        if geo:
            self.restoreGeometry(geo)

    def closeEvent(self, event):
        self.config.save_window_geometry(self.saveGeometry())
        self.logger.info("🔒 Приложение закрыто")
        event.accept()
