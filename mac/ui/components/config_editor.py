import os
import re

from PyQt6.QtCore import QObject, QThread, QTimer, Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from core.ssh_client import (
    cleanup_remote_backups,
    create_remote_backup,
    delete_remote_backup,
    download_cfg_via_ssh,
    ensure_remote_backup_exists,
    list_remote_backups,
    restore_remote_backup,
    sha256_local_file,
    sha256_remote_file_via_sftp,
    upload_cfg_via_ssh,
)
from utils.logger import get_logger
from utils.strings import S


class _SshDownloadWorker(QObject):
    finished = pyqtSignal(bool, str, str)

    def __init__(self, ip: str, port: int, user: str, pwd: str, remote_path: str):
        super().__init__()
        self.ip = ip
        self.port = port
        self.user = user
        self.pwd = pwd
        self.remote_path = remote_path

    def run(self):
        try:
            local_path = download_cfg_via_ssh(self.ip, self.port, self.user, self.pwd, self.remote_path)
            if local_path:
                self.finished.emit(True, local_path, "")
            else:
                self.finished.emit(False, "", "download_cfg_via_ssh returned None")
        except Exception as error:
            self.finished.emit(False, "", str(error))


class _SshUploadWorker(QObject):
    finished = pyqtSignal(bool, str)

    def __init__(
        self,
        local_path: str,
        ip: str,
        port: int,
        user: str,
        pwd: str,
        remote_path: str,
        create_backup: bool = True,
    ):
        super().__init__()
        self.local_path = local_path
        self.ip = ip
        self.port = port
        self.user = user
        self.pwd = pwd
        self.remote_path = remote_path
        self.create_backup = create_backup
        self.logger = get_logger(__name__)

    def run(self):
        try:
            local_sha = sha256_local_file(self.local_path)
            self.logger.info("SSH upload verify: local_sha256=%s local_path=%s", local_sha, self.local_path)

            if self.create_backup:
                backup_path = create_remote_backup(self.ip, self.port, self.user, self.pwd, self.remote_path)
                if not backup_path:
                    self.finished.emit(False, "backup_failed")
                    return
                self.logger.info("SSH upload verify: backup_created=%s", backup_path)

            ok = upload_cfg_via_ssh(self.local_path, self.ip, self.port, self.user, self.pwd, self.remote_path)
            if not ok:
                self.finished.emit(False, "upload_failed")
                return

            remote_sha = sha256_remote_file_via_sftp(self.ip, self.port, self.user, self.pwd, self.remote_path)
            if not remote_sha:
                self.finished.emit(False, "verify_failed")
                return
            if remote_sha != local_sha:
                self.logger.error(
                    "SSH upload verify mismatch: local=%s remote=%s remote_path=%s",
                    local_sha,
                    remote_sha,
                    self.remote_path,
                )
                self.finished.emit(False, "verify_failed")
                return
            self.logger.info("SSH upload verify ok: sha256=%s", remote_sha)

            cleanup_remote_backups(self.ip, self.port, self.user, self.pwd, self.remote_path)
            self.finished.emit(True, "")
        except Exception as error:
            self.finished.emit(False, str(error))


class _SshBackupWorker(QObject):
    finished = pyqtSignal(bool, object, str)

    def __init__(
        self,
        action: str,
        ip: str,
        port: int,
        user: str,
        pwd: str,
        remote_path: str,
        backup_path: str | None = None,
    ):
        super().__init__()
        self.action = action
        self.ip = ip
        self.port = port
        self.user = user
        self.pwd = pwd
        self.remote_path = remote_path
        self.backup_path = backup_path
        self.logger = get_logger(__name__)

    def run(self):
        try:
            if self.action == "list":
                self.finished.emit(True, list_remote_backups(self.ip, self.port, self.user, self.pwd, self.remote_path), "")
                return
            if self.action == "ensure":
                created = ensure_remote_backup_exists(self.ip, self.port, self.user, self.pwd, self.remote_path, max_backups=5)
                self.finished.emit(True, created, "")
                return
            if self.action == "create":
                created = create_remote_backup(self.ip, self.port, self.user, self.pwd, self.remote_path)
                if not created:
                    self.finished.emit(False, None, "create_failed")
                    return
                cleanup_remote_backups(self.ip, self.port, self.user, self.pwd, self.remote_path, max_backups=5)
                self.finished.emit(True, created, "")
                return
            if self.action == "restore":
                if not self.backup_path:
                    self.finished.emit(False, None, "no_backup_selected")
                    return
                ok = restore_remote_backup(self.ip, self.port, self.user, self.pwd, self.backup_path, self.remote_path)
                self.finished.emit(ok, self.backup_path, "" if ok else "restore_failed")
                return
            if self.action == "delete":
                if not self.backup_path:
                    self.finished.emit(False, None, "no_backup_selected")
                    return
                ok = delete_remote_backup(self.ip, self.port, self.user, self.pwd, self.backup_path)
                self.finished.emit(ok, self.backup_path, "" if ok else "delete_failed")
                return
            self.finished.emit(False, None, f"unknown_action:{self.action}")
        except Exception as error:
            self.finished.emit(False, None, str(error))


class KlipperConfigParser:
    def __init__(self, filepath):
        self.filepath = filepath
        self.raw_lines = []
        self.sections = {}

    def load(self):
        if not os.path.exists(self.filepath):
            return

        with open(self.filepath, "r", encoding="utf-8") as file_obj:
            self.raw_lines = file_obj.readlines()

        self.sections.clear()
        current_section = None

        for index, line in enumerate(self.raw_lines):
            stripped = line.strip()

            if not stripped or stripped.startswith("#"):
                continue

            match = re.match(r"^\[(.+)\]$", stripped)
            if match:
                current_section = match.group(1)
                if current_section not in self.sections:
                    self.sections[current_section] = {}
                continue

            if current_section and ":" in stripped and not stripped.startswith("#"):
                parts = stripped.split(":", 1)
                if len(parts) == 2:
                    key = parts[0].strip()
                    val_part = parts[1].split("#")[0].strip()
                    self.sections[current_section][key] = (val_part, index)


class ConfigEditor(QWidget):
    ssh_operation_finished = pyqtSignal()
    ssh_download_succeeded = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.logger = get_logger(__name__)
        self.parser = None
        self.widgets = {}
        self._ace_pending: dict[str, str] = {}
        self._file_path = None
        self._ssh_config = None
        self._ssh_thread = None
        self._ssh_worker = None
        self._ssh_upload_thread = None
        self._ssh_upload_worker = None
        self._ssh_backup_thread = None
        self._ssh_backup_worker = None
        self._auto_backup_done = False
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)

        self.backup_group = QGroupBox("🧰 Бекапы printer.cfg")
        self.backup_group.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        b_layout = QVBoxLayout(self.backup_group)
        b_layout.setContentsMargins(8, 8, 8, 8)

        header = QHBoxLayout()
        self.backup_status = QLabel("—")
        self.backup_status.setStyleSheet("color: #888;")
        header.addWidget(self.backup_status)
        header.addStretch()
        self.btn_backup_refresh = QPushButton("🔄 Обновить")
        self.btn_backup_refresh.setFixedHeight(26)
        header.addWidget(self.btn_backup_refresh)
        b_layout.addLayout(header)

        self.backup_list = QListWidget()
        self.backup_list.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.backup_list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.backup_list.setUniformItemSizes(True)
        self.backup_list.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        self.backup_list.setStyleSheet("background: #1e1e1e; color: #d4d4d4; border: 1px solid #444;")
        b_layout.addWidget(self.backup_list)

        btn_row = QHBoxLayout()
        self.btn_backup_create = QPushButton("📦 Создать бекап")
        self.btn_backup_restore = QPushButton("⏪ Восстановить")
        self.btn_backup_delete = QPushButton("🗑 Удалить")
        btn_row.addWidget(self.btn_backup_create)
        btn_row.addWidget(self.btn_backup_restore)
        btn_row.addWidget(self.btn_backup_delete)
        btn_row.addStretch()
        b_layout.addLayout(btn_row)

        layout.addWidget(self.backup_group)

        toolbar = QHBoxLayout()
        self.btn_load = QPushButton(S.get("config.btn_load"))
        self.btn_save = QPushButton(S.get("config.btn_save"))
        self.btn_save.setEnabled(False)
        self.btn_save.setStyleSheet("background-color: #2d5a2d; color: white;")

        toolbar.addWidget(self.btn_load)
        toolbar.addWidget(self.btn_save)
        toolbar.addStretch()

        self.status = QLabel(S.get("config.status_ready"))
        self.status.setStyleSheet("color: #888;")
        toolbar.addWidget(self.status)

        layout.addLayout(toolbar)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        self.container = QWidget()
        self.container_layout = QVBoxLayout(self.container)
        self.container_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        scroll.setWidget(self.container)
        layout.addWidget(scroll)

        self.btn_load.clicked.connect(self.load_file)
        self.btn_save.clicked.connect(self.save_to_printer)
        self.btn_backup_refresh.clicked.connect(self._refresh_backups)
        self.btn_backup_create.clicked.connect(lambda: self._run_backup_action("create"))
        self.btn_backup_restore.clicked.connect(lambda: self._run_backup_action("restore"))
        self.btn_backup_delete.clicked.connect(lambda: self._run_backup_action("delete"))

    def set_ssh_config(self, config):
        self._ssh_config = config

    def load_from_ssh_data(self, ssh_data):
        if self._ssh_thread and self._ssh_thread.isRunning():
            self.logger.warning("SSH download requested while previous still running")
            return

        ip = ssh_data.get("ip")
        try:
            port = int(ssh_data.get("port", 2222))
        except ValueError:
            port = 2222

        user = ssh_data.get("user", "root")
        pwd = ssh_data.get("password", "")
        remote_path = ssh_data.get("path", "/userdata/app/gk/printer.cfg")

        safe_ssh_data = dict(ssh_data or {})
        if "password" in safe_ssh_data:
            safe_ssh_data["password"] = "***"
        self.logger.info("SSH UI download requested: %s", safe_ssh_data)

        self._ssh_config = {
            "ip": ip,
            "port": port,
            "user": user,
            "password": pwd,
            "path": remote_path,
        }

        self.status.setText(f"⏳ Подключение к {ip}...")
        self.repaint()

        self._ssh_thread = QThread(self)
        self._ssh_worker = _SshDownloadWorker(ip, port, user, pwd, remote_path)
        self._ssh_worker.moveToThread(self._ssh_thread)

        self._ssh_thread.started.connect(self._ssh_worker.run)
        self._ssh_worker.finished.connect(self._on_ssh_download_finished)
        self._ssh_worker.finished.connect(self._ssh_thread.quit)
        self._ssh_thread.finished.connect(self._ssh_thread.deleteLater)
        self._ssh_thread.start()

    def _on_ssh_download_finished(self, ok: bool, local_path: str, error_text: str):
        try:
            ip = self._ssh_config.get("ip") if self._ssh_config else ""
            if ok and local_path:
                self.logger.info("SSH UI download success: local_path=%s", local_path)
                self.status.setText("⏳ Обработка файла...")
                self.repaint()
                self._process_loaded_file(local_path)
                self.btn_save.setEnabled(True)
                self.status.setText(f"✅ Загружено с принтера ({ip})")
                self.ssh_download_succeeded.emit(local_path)

                if not self._auto_backup_done and self._ssh_config:
                    self._auto_backup_done = True
                    self._run_backup_action("ensure", silent=True)
                else:
                    self._refresh_backups()
            else:
                self.logger.error("SSH UI download failed: %s", error_text)
                QMessageBox.critical(
                    self,
                    "Ошибка SSH",
                    "Не удалось скачать файл.\nПроверьте настройки подключения.\nПодробности в debug.log",
                )
                self.status.setText("❌ Ошибка загрузки")
        finally:
            self._ssh_worker = None
            self._ssh_thread = None
            self.ssh_operation_finished.emit()

    def _refresh_backups(self):
        self._run_backup_action("list", silent=True)

    def _selected_backup_path(self) -> str | None:
        item = self.backup_list.currentItem()
        return item.text() if item else None

    def _run_backup_action(self, action: str, silent: bool = False):
        if not self._ssh_config:
            if not silent:
                QMessageBox.information(self, "Бекапы", "Подключитесь по SSH, чтобы управлять бекапами.")
            return
        if self._ssh_backup_thread and self._ssh_backup_thread.isRunning():
            return

        ip = self._ssh_config["ip"]
        port = self._ssh_config["port"]
        user = self._ssh_config["user"]
        pwd = self._ssh_config["password"]
        remote_path = self._ssh_config["path"]
        backup_path = self._selected_backup_path()

        self.backup_status.setText(f"⏳ {action}...")
        self._ssh_backup_thread = QThread(self)
        self._ssh_backup_worker = _SshBackupWorker(action, ip, port, user, pwd, remote_path, backup_path=backup_path)
        self._ssh_backup_worker.moveToThread(self._ssh_backup_thread)
        self._ssh_backup_thread.started.connect(self._ssh_backup_worker.run)
        self._ssh_backup_worker.finished.connect(
            lambda ok, payload, err: self._on_backup_action_finished(action, ok, payload, err, silent)
        )
        self._ssh_backup_worker.finished.connect(self._ssh_backup_thread.quit)
        self._ssh_backup_thread.finished.connect(self._ssh_backup_thread.deleteLater)
        self._ssh_backup_thread.start()

    def _on_backup_action_finished(self, action: str, ok: bool, payload: object, error_text: str, silent: bool):
        should_refresh = False
        try:
            if action == "list" and ok:
                self.backup_list.clear()
                for path in payload or []:
                    self.backup_list.addItem(str(path))
                self._update_backup_list_height()
                self.backup_status.setText(f"✅ Бекапов: {self.backup_list.count()} (лимит 5)")
                return

            if action in ("ensure", "create", "restore", "delete") and ok:
                self.backup_status.setText("✅ Готово")
                should_refresh = True

            if not ok:
                self.backup_status.setText("❌ Ошибка")
                if not silent:
                    QMessageBox.warning(self, "Бекапы", f"Операция не выполнена: {action}\n{error_text}")
        finally:
            self._ssh_backup_worker = None
            self._ssh_backup_thread = None
            if should_refresh:
                QTimer.singleShot(0, self._refresh_backups)

    def _update_backup_list_height(self, max_rows: int = 5):
        rows = min(self.backup_list.count(), max_rows)
        if rows <= 0:
            row_h = max(self.fontMetrics().height() + 6, 18)
            rows = 1
        else:
            row_h = self.backup_list.sizeHintForRow(0)
            if row_h <= 0:
                row_h = max(self.fontMetrics().height() + 6, 18)

        frame = self.backup_list.frameWidth() * 2
        height = frame + (row_h * rows) + 2
        self.backup_list.setFixedHeight(height)

    def load_file(self, path=None):
        if not path:
            path, _ = QFileDialog.getOpenFileName(self, "Выберите printer.cfg", "", "Config Files (*.cfg);;All Files (*)")

        if not path or not os.path.exists(path):
            return

        self._process_loaded_file(path)
        self.btn_save.setEnabled(False)

    def _process_loaded_file(self, path):
        try:
            self.logger.info("Config processing start: path=%s", path)
            self.parser = KlipperConfigParser(path)
            self.parser.load()
            self._file_path = path
            self._ace_pending = {}
            self._build_ui()
            self.btn_save.setEnabled(False)
            self.status.setText(S.get("config.status_loaded", filename=os.path.basename(path)))
            self.logger.info(
                "Config processing done: sections=%s file_path=%s",
                len(self.parser.sections) if self.parser else None,
                self._file_path,
            )
        except Exception as error:
            self.logger.exception("Config processing failed: path=%s error=%s", path, error)
            QMessageBox.critical(self, "Ошибка", S.get("config.msg_load_error", error=str(error)))

    def _build_ui(self):
        self.logger.debug(
            "Build UI start: sections_present=%s",
            list(self.parser.sections.keys())[:10] if self.parser and self.parser.sections else [],
        )
        while self.container_layout.count():
            item = self.container_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.widgets.clear()

        if not self.parser or not self.parser.sections:
            self.status.setText(S.get("config.status_empty"))
            self.logger.warning("Build UI: no sections parsed")
            return

        target_sections = ["bed_mesh", "filament_hub"]

        for sec_name in target_sections:
            if sec_name not in self.parser.sections:
                self.logger.warning("Build UI: section not found: %s", sec_name)
                continue

            sec_meta_key = f"config.sections.{sec_name}"
            sec_data = S.get(sec_meta_key, title=f"⚙️ [{sec_name}]")
            if isinstance(sec_data, str):
                self.logger.warning("Build UI: locale/meta missing for %s (got str)", sec_meta_key)
                sec_data = {"title": f"⚙️ [{sec_name}]", "fields": {}}
            fields_meta = sec_data.get("fields", {}) if isinstance(sec_data, dict) else {}

            group = QGroupBox(sec_data.get("title") if isinstance(sec_data, dict) else f"⚙️ [{sec_name}]")
            form = QFormLayout()
            group.setLayout(form)

            has_fields = False

            if sec_name == "filament_hub" and isinstance(fields_meta, dict) and (
                "ace_feed_speed" in fields_meta or "ace_unwind_speed" in fields_meta
            ):
                standard = {
                    "v1_unwind_speed": "20",
                    "v2_unwind_speed": "20",
                    "v1_feed_speed": "30",
                    "v2_feed_speed": "30",
                    "unwind_speed_old_ace": "15",
                    "unwind_length_after_triggered": "1300",
                }
                optimized = {
                    "unwind_length_after_triggered": "1220",
                }

                preset_row = QWidget()
                preset_layout = QHBoxLayout(preset_row)
                preset_layout.setContentsMargins(0, 0, 0, 0)
                cb_preset = QComboBox()
                cb_preset.setStyleSheet("background: #2b2b2b; color: #d4d4d4; border: 1px solid #444; padding: 4px;")
                cb_preset.addItems(["100%", "150%", "200%", "250%", "300%"])
                cb_preset.setMinimumWidth(110)
                try:
                    cb_preset.view().setMinimumWidth(110)
                except Exception:
                    pass

                def _apply_preset():
                    pct_text = (cb_preset.currentText() or "100%").strip().replace("%", "")
                    try:
                        pct = int(pct_text)
                    except Exception:
                        pct = 100
                    factor = max(0, pct) / 100.0 if pct else 1.0
                    use_optimized = pct != 100

                    def _scale_int(value: str) -> str:
                        try:
                            return str(int(round(float(value) * factor)))
                        except Exception:
                            return value

                    self._ace_pending = {
                        "v2_unwind_speed": _scale_int(standard["v2_unwind_speed"]),
                        "v1_unwind_speed": _scale_int(standard["v1_unwind_speed"]),
                        "v2_feed_speed": _scale_int(standard["v2_feed_speed"]),
                        "v1_feed_speed": _scale_int(standard["v1_feed_speed"]),
                        "unwind_speed_old_ace": _scale_int(standard["unwind_speed_old_ace"]),
                        "unwind_length_after_triggered": (
                            optimized if use_optimized else standard
                        )["unwind_length_after_triggered"],
                    }

                    self._on_changed()

                cb_preset.currentTextChanged.connect(lambda _: _apply_preset())

                preset_layout.addWidget(cb_preset)
                preset_layout.addStretch()
                form.addRow("Ускорение Ace Pro:", preset_row)
                has_fields = True

            else:
                for key, (val, _line_idx) in self.parser.sections[sec_name].items():
                    meta = fields_meta.get(key)
                    if not meta:
                        continue

                    label = meta.get("label", key)
                    placeholder = meta.get("ph", "")
                    tooltip = meta.get("tip", "")

                    if key == "algorithm":
                        cb = QComboBox()
                        cb.setStyleSheet("background: #2b2b2b; color: #d4d4d4; border: 1px solid #444; padding: 4px;")
                        cb.setToolTip(tooltip)
                        cb.addItems(["lagrange", "bicubic"])
                        current = (val or "").strip()
                        idx = cb.findText(current)
                        if idx >= 0:
                            cb.setCurrentIndex(idx)
                        cb.currentTextChanged.connect(self._on_changed)
                        editor_widget = cb
                    else:
                        display_val = self._display_bed_mesh_value(key, val)
                        le = QLineEdit(display_val)
                        le.setStyleSheet("background: #2b2b2b; color: #d4d4d4; border: 1px solid #444; padding: 4px;")
                        le.setPlaceholderText(placeholder)
                        le.setToolTip(tooltip)
                        le.textChanged.connect(self._on_changed)
                        editor_widget = le

                    form.addRow(f"{label}:", editor_widget)
                    self.widgets[(sec_name, key)] = editor_widget
                    has_fields = True

            if has_fields:
                self.container_layout.addWidget(group)

        self.container_layout.addStretch()
        self.logger.debug("Build UI done: widgets=%s", len(self.widgets))

    def _on_changed(self):
        self.btn_save.setEnabled(True)

    def save_to_printer(self):
        if not self._ssh_config:
            QMessageBox.warning(self, "Ошибка", "Настройки SSH не заданы. Загрузите файл по SSH сначала.")
            return

        if not self._save_file_changes(silent=True):
            return

        ip = self._ssh_config["ip"]
        port = self._ssh_config["port"]
        user = self._ssh_config["user"]
        pwd = self._ssh_config["password"]
        remote_path = self._ssh_config["path"]

        self.logger.info(
            "SSH UI upload requested: host=%s port=%s user=%s remote_path=%s local_path=%s",
            ip,
            port,
            user,
            remote_path,
            self._file_path,
        )

        if self._ssh_upload_thread and self._ssh_upload_thread.isRunning():
            QMessageBox.information(self, "SSH", "Операция сохранения уже выполняется.")
            return

        self.status.setText("⏳ Сохранение на принтер...")
        self.repaint()

        self._ssh_upload_thread = QThread(self)
        self._ssh_upload_worker = _SshUploadWorker(self._file_path, ip, port, user, pwd, remote_path)
        self._ssh_upload_worker.moveToThread(self._ssh_upload_thread)

        self._ssh_upload_thread.started.connect(self._ssh_upload_worker.run)
        self._ssh_upload_worker.finished.connect(self._on_ssh_upload_finished)
        self._ssh_upload_worker.finished.connect(self._ssh_upload_thread.quit)
        self._ssh_upload_thread.finished.connect(self._ssh_upload_thread.deleteLater)
        self._ssh_upload_thread.start()

    def _on_ssh_upload_finished(self, ok: bool, error_text: str):
        try:
            if ok:
                self.logger.info(
                    "SSH UI upload success: remote_path=%s",
                    self._ssh_config.get("path") if self._ssh_config else None,
                )
                self.status.setText("✅ Сохранено на принтер")
                QMessageBox.information(self, "Успех", "Файл отправлен. Бэкап создан. Не забудьте перезагрузить принтер.")
                return

            if error_text == "backup_failed":
                reply = QMessageBox.question(
                    self,
                    "Предупреждение",
                    "Не удалось создать бекап на принтере. Продолжить сохранение без бекапа?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                )
                if reply == QMessageBox.StandardButton.No:
                    self.status.setText("❌ Отменено")
                    return

                ip = self._ssh_config["ip"]
                port = self._ssh_config["port"]
                user = self._ssh_config["user"]
                pwd = self._ssh_config["password"]
                remote_path = self._ssh_config["path"]

                self.status.setText("⏳ Отправка файла...")
                self.repaint()

                self._ssh_upload_thread = QThread(self)
                self._ssh_upload_worker = _SshUploadWorker(
                    self._file_path,
                    ip,
                    port,
                    user,
                    pwd,
                    remote_path,
                    create_backup=False,
                )
                self._ssh_upload_worker.moveToThread(self._ssh_upload_thread)
                self._ssh_upload_thread.started.connect(self._ssh_upload_worker.run)
                self._ssh_upload_worker.finished.connect(self._on_ssh_upload_finished)
                self._ssh_upload_worker.finished.connect(self._ssh_upload_thread.quit)
                self._ssh_upload_thread.finished.connect(self._ssh_upload_thread.deleteLater)
                self._ssh_upload_thread.start()
                return

            self.logger.error("SSH UI upload failed: %s", error_text)
            QMessageBox.critical(self, "Ошибка", "Не удалось загрузить файл на принтер.")
            self.status.setText("❌ Ошибка отправки")
        finally:
            self._ssh_upload_worker = None
            self._ssh_upload_thread = None
            self.ssh_operation_finished.emit()

    def _save_file_changes(self, silent=False):
        if not self.parser or not self._file_path:
            return False

        try:
            changed = False

            def _set_key_value(sec: str, key: str, new_val: str) -> bool:
                nonlocal changed
                if sec not in self.parser.sections or key not in self.parser.sections[sec]:
                    return False
                old_val, line_idx = self.parser.sections[sec][key]
                if new_val == old_val:
                    return False
                original_line = self.parser.raw_lines[line_idx]
                indent = original_line[: len(original_line) - len(original_line.lstrip())]
                self.parser.raw_lines[line_idx] = f"{indent}{key}: {new_val}\n"
                changed = True
                return True

            for (sec, key), widget in self.widgets.items():
                new_val = self._get_widget_value(widget).strip()
                new_val = self._normalize_bed_mesh_value(key, new_val, widget if isinstance(widget, QLineEdit) else None)
                _set_key_value(sec, key, new_val)

            if self._ace_pending:
                for key, value in (self._ace_pending or {}).items():
                    _set_key_value("filament_hub", key, str(value).strip())

            if changed:
                with open(self._file_path, "w", encoding="utf-8") as file_obj:
                    file_obj.writelines(self.parser.raw_lines)
                self.parser.load()

            self.btn_save.setEnabled(False)

            if not silent:
                self.status.setText(S.get("config.status_saved"))
                QMessageBox.information(self, S.get("config.msg_save_ok_title"), S.get("config.msg_save_ok_text"))

            return True
        except Exception as error:
            if not silent:
                QMessageBox.critical(self, "Ошибка", str(error))
            return False

    def _get_widget_value(self, widget: QWidget) -> str:
        if isinstance(widget, QLineEdit):
            return widget.text()
        if isinstance(widget, QComboBox):
            return widget.currentText()
        return ""

    def _display_bed_mesh_value(self, key: str, raw_val: str) -> str:
        if key not in ("mesh_min", "mesh_max", "probe_count"):
            return raw_val
        if raw_val is None:
            return ""
        value = str(raw_val).strip()
        parts = [part.strip() for part in value.split(",")]
        if len(parts) != 2:
            return value
        first, second = parts[0], parts[1]
        if first == "" or second == "":
            return value
        if first == second:
            return first
        return value

    def _normalize_bed_mesh_value(self, key: str, value: str, le: QLineEdit | None = None) -> str:
        del le
        if key not in ("mesh_min", "mesh_max", "probe_count"):
            return value
        normalized = (value or "").strip()
        if not normalized:
            return normalized
        if "," in normalized:
            return normalized
        num_re = r"\d+" if key == "probe_count" else r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)"
        if re.fullmatch(num_re, normalized):
            return f"{normalized},{normalized}"
        return normalized

    def load_from_path(self, path):
        self.load_file(path)
