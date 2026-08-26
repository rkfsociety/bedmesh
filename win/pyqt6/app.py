import sys
import numpy as np
import os
import traceback
import json
from PyQt6.QtWidgets import QMainWindow, QSplitter, QVBoxLayout, QWidget, QMessageBox
from PyQt6.QtCore import Qt, pyqtSignal, QObject, QThread

from ui.panels.left_panel import LeftPanel
from ui.panels.right_panel import RightPanel
from ui.panels.center_tabs import CenterTabs
from core.mesh_parser import MeshParser, BedMeshData
from core.ssh_client import (
    download_cfg_via_ssh,
    get_ssh_connection,
    send_gcode_via_temporary_bridge,
    BED_MESH_CALIBRATION_COMMANDS,
)
from core.live_mesh import LiveMeshAccumulator
from utils.logger import get_logger
from utils.app_config import AppConfig
from utils.strings import S
from utils.version import VERSION
from utils import updater


class _CalibrationWorker(QObject):
    snapshot = pyqtSignal(object)
    status = pyqtSignal(str)
    finished = pyqtSignal(bool, str)

    def __init__(self, ssh_data: dict):
        super().__init__()
        self.ssh_data = ssh_data

    def run(self):
        monitor = None
        stdout = None
        accumulator = LiveMeshAccumulator()
        try:
            ip = self.ssh_data.get("ip", "")
            port = int(self.ssh_data.get("port", 2222))
            user = self.ssh_data.get("user", "root")
            password = self.ssh_data.get("password", "")
            monitor = get_ssh_connection(ip, port, user, password)
            self.status.emit("Подключено. Читаю параметры сетки...")
            _, mesh_stdout, _ = monitor.exec_command(
                "cat /userdata/app/gk/printer_mutable.cfg 2>/dev/null"
            )
            try:
                mesh_cfg = json.loads(mesh_stdout.read().decode("utf-8", errors="replace"))
                mesh = mesh_cfg.get("bed_mesh default", {})
                x_count = int(mesh.get("x_count", 0))
                y_count = int(mesh.get("y_count", 0))
                x_min, x_max = float(mesh.get("min_x", 0)), float(mesh.get("max_x", 0))
                y_min, y_max = float(mesh.get("min_y", 0)), float(mesh.get("max_y", 0))
                if x_count > 0 and y_count > 0 and x_max > x_min and y_max > y_min:
                    accumulator = LiveMeshAccumulator(
                        total_points=x_count * y_count,
                        x=np.linspace(x_min, x_max, x_count),
                        y=np.linspace(y_min, y_max, y_count),
                    )
            except (json.JSONDecodeError, TypeError, ValueError, UnicodeError):
                self.status.emit("Параметры сетки не прочитаны, определяю её по точкам...")
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
                    self.finished.emit(
                        False,
                        f"Не удалось отправить штатную команду {command} по SSH.\n{details}",
                    )
                    return

            import time
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
                        f"Измерение точки {len(accumulator.points)}/{accumulator.total_points or '?'}: "
                        f"X={point[0]:.1f} Y={point[1]:.1f}"
                    )
                    self.snapshot.emit(accumulator.snapshot())
                else:
                    if line:
                        upper = line.upper()
                        if "LEVIQ2_PREHEATING" in upper or "CMD_LEVIQ3_PREHEATING" in upper:
                            self.status.emit("Принтер прогревает стол и сопло...")
                        elif "LEVIQ2_WIPING" in upper or "WIPING" in upper:
                            self.status.emit("Принтер очищает сопло...")
                        elif "CMD_G28" in upper or "G28 Z" in upper:
                            self.status.emit("Принтер выполняет хоуминг Z...")
                        elif "LEVIQ2_PROBE" in upper:
                            self.status.emit("Принтер измеряет стол тензодатчиком...")
                        elif "SAVE_CONFIG" in upper or "SAVE_CONFIG" in line:
                            self.status.emit("Принтер сохраняет карту...")
                    time.sleep(0.15)
                if accumulator.points:
                    if now - idle_since >= idle_timeout:
                        break
                elif now >= first_point_deadline:
                    self.finished.emit(
                        False,
                        "Принтер не передал ни одной точки за 3 минуты. "
                        "Калибровка могла не начаться или журнал недоступен.",
                    )
                    return
            self.finished.emit(
                True,
                f"Получено точек: {len(accumulator.points)}. "
                "Нажмите «Загрузить по SSH» для итоговой карты.",
            )
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
        # Дублируем иконку приложения на окно, чтобы она стабильно отображалась на Windows (в т.ч. в панели задач).
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

        # Quiet update check: update status in right panel, no popup.
        self.right_panel.clear_update_available(f"v{VERSION}")
        self.right_panel.set_update_handler(self._on_update_button_clicked)
        self._update_release_data = None
        self._update_check_done.connect(self._apply_update_check_result)
        self._check_updates_quiet()

    def _init_ui(self):
        self.setWindowTitle(f"{S.get('app.title')} v{VERSION}")
        self.setMinimumWidth(1100)
        self.resize(1500, 860)

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(8, 8, 8, 8)

        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        layout.addWidget(self.splitter)

        self.left_panel = LeftPanel(self.settings)
        self.center_tabs = CenterTabs()
        self.right_panel = RightPanel()

        # Применяем палитру и режим карты из настроек
        self.center_tabs.set_mesh_palette(self.settings.get("mesh_palette", "soft"))
        self.center_tabs.view_mode_changed.connect(self._on_view_mode_changed)

        self.splitter.addWidget(self.left_panel)
        self.splitter.addWidget(self.center_tabs)
        self.splitter.addWidget(self.right_panel)

        self.splitter.setStretchFactor(0, 1)
        self.splitter.setStretchFactor(1, 4)
        self.splitter.setStretchFactor(2, 2)
        self.splitter.setSizes([245, 1110, 385])

        # --- Коннекты ---
        # SSH загрузка через ConfigEditor
        self.left_panel.ssh_download_requested.connect(self._handle_ssh_load_via_editor)
        self.left_panel.calibration_requested.connect(self._start_calibration)
        
        # Сброс кнопки в левой панели после завершения операции в редакторе
        self.center_tabs.config_editor.ssh_operation_finished.connect(self.left_panel.reset_ssh_button)
        # После успешной SSH-загрузки — обновляем RAW и пробуем построить карту
        self.center_tabs.config_editor.ssh_download_succeeded.connect(self._handle_ssh_file_downloaded)
        
        self.left_panel.setting_updated.connect(self._on_setting_changed)
        self.left_panel.advanced_toggled.connect(self.center_tabs.set_advanced_visible)

        saved_mode = self.settings.get("mesh_view_mode", "2d")
        if saved_mode == "3d":
            self.center_tabs.set_view_mode("3d")

    def _check_updates_quiet(self):
        self.right_panel.set_checking_updates(True)

        def on_result(status: str, latest_tag: str | None, data: dict | None):
            # Emit to GUI thread.
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
        # If update is available -> install; otherwise -> manual check
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
        """Передает управление загрузкой по SSH в ConfigEditor"""
        try:
            self._last_ssh_data = ssh_data
            # Не переключаем вкладки при старте SSH-загрузки, чтобы избежать "мигания":
            # по завершении загрузки `_process_file` сам переключит на карту, если mesh найден,
            # а иначе останемся на RAW (см. `_handle_ssh_file_downloaded`).
            self.center_tabs.config_editor.load_from_ssh_data(ssh_data)
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось инициировать загрузку:\n{str(e)}")
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
        # После SSH-загрузки пробуем построить карту.
        # Важно: не переключаем вкладки "вслепую", иначе можно перебить переход на вкладку карты.
        try:
            has_mesh = self._process_file(local_path, allow_remote_fallback=True)
            if not has_mesh:
                self.center_tabs.tabs.setCurrentWidget(self.center_tabs.raw_tab)
        except Exception as e:
            self.logger.exception("SSH file post-process failed: %s", e)
        # Раз SSH сейчас работает — определяем, что из автозапуска уже установлено на принтере.
        try:
            self.left_panel.refresh_persist_status()
        except Exception as e:
            self.logger.exception("persist status refresh failed: %s", e)

    def _process_file(self, filepath, *, allow_remote_fallback: bool = False):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                raw_content = f.read()
            self.center_tabs.raw_text.setPlainText(raw_content)

            data = self.parser.parse_text(raw_content)

            if data:
                self._last_mesh_data = data
                self.center_tabs.update_mesh_views(data)
                stats = self._calculate_advanced_stats(data)
                self.right_panel.update_all(stats)
                self.right_panel.update_shaper(self.parser.parse_input_shaper_text(raw_content))
                self.logger.info(f"✅ Mesh загружен: {data.x_count}x{data.y_count}")
                self.center_tabs.tabs.setCurrentWidget(self.center_tabs.mesh_tab)
                return True
            else:
                # printer.cfg часто содержит только настройки bed_mesh, а сохранённые points лежат в printer_mutable.cfg.
                mutable_path = "/userdata/app/gk/printer_mutable.cfg"
                if self._last_ssh_data and allow_remote_fallback:
                    ip = self._last_ssh_data.get("ip")
                    port = int(self._last_ssh_data.get("port", 2222))
                    user = self._last_ssh_data.get("user", "root")
                    pwd = self._last_ssh_data.get("password", "")
                    self.logger.info("No mesh points in %s, trying SSH download: %s", filepath, mutable_path)
                    alt_local = download_cfg_via_ssh(ip, port, user, pwd, mutable_path)
                    if alt_local:
                        # Показываем в RAW реальный файл, из которого берём points.
                        alt_content = None
                        try:
                            with open(alt_local, 'r', encoding='utf-8') as f:
                                alt_content = f.read()
                            self.center_tabs.raw_text.setPlainText(alt_content)
                        except Exception:
                            # RAW — вспомогательная вкладка; не ломаем основной флоу из-за ошибки чтения.
                            self.logger.exception("Failed to update RAW from %s", alt_local)
                        alt_data = self.parser.parse_text(alt_content) if alt_content is not None else None
                        if alt_data:
                            # Размер печати находится в основном printer.cfg,
                            # а точки mesh часто лежат в printer_mutable.cfg.
                            print_size = self.parser.parse_print_size(raw_content)
                            if print_size:
                                alt_data.bed_min_x = 0.0
                                alt_data.bed_max_x = print_size[0]
                                alt_data.bed_min_y = 0.0
                                alt_data.bed_max_y = print_size[1]
                            self._last_mesh_data = alt_data
                            self.center_tabs.update_mesh_views(alt_data)
                            stats = self._calculate_advanced_stats(alt_data)
                            self.right_panel.update_all(stats)
                            # Шейпер ищем сначала в mutable, потом в основном файле
                            shaper = (
                                self.parser.parse_input_shaper_text(alt_content)
                                if alt_content is not None
                                else None
                            ) or self.parser.parse_input_shaper_text(raw_content)
                            self.right_panel.update_shaper(shaper)
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
        residual = z_flat - mean_val
        return {
            "min": min_val, "max": max_val, "range": float(max_val - min_val),
            "mean": mean_val, "var": float(np.var(z_flat)),
            "rms": float(np.sqrt(np.mean(residual**2))),
            "front_left": float(data.z[0, 0] - mean_val),
            "front_right": float(data.z[0, -1] - mean_val),
            "back_center": float(data.z[-1, data.x_count // 2] - mean_val)
        }

    def _restore_geometry(self):
        geo = self.config.get_window_geometry()
        if geo:
            self.restoreGeometry(geo)

    def closeEvent(self, event):
        self.left_panel.flush_pending_settings()
        self.config.save_window_geometry(self.saveGeometry())
        self.logger.info("🔒 Приложение закрыто")
        event.accept()
