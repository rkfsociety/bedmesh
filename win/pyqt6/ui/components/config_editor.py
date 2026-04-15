import os
import re
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                             QLabel, QFileDialog, QScrollArea, QFormLayout,
                             QGroupBox, QLineEdit, QMessageBox, QListWidget, QComboBox, QSizePolicy)
from PyQt6.QtCore import Qt, pyqtSignal, QObject, QThread, QTimer
from utils.strings import S
from utils.logger import get_logger
from core.ssh_client import (
    download_cfg_via_ssh, 
    upload_cfg_via_ssh, 
    create_remote_backup,
    cleanup_remote_backups,
    sha256_local_file,
    sha256_remote_file_via_sftp,
    list_remote_backups,
    restore_remote_backup,
    delete_remote_backup,
    ensure_remote_backup_exists,
)

class _SshDownloadWorker(QObject):
    finished = pyqtSignal(bool, str, str)  # ok, local_path, error_text

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
        except Exception as e:
            self.finished.emit(False, "", str(e))

class _SshUploadWorker(QObject):
    finished = pyqtSignal(bool, str)  # ok, error_text

    def __init__(self, local_path: str, ip: str, port: int, user: str, pwd: str, remote_path: str, create_backup: bool = True):
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
                    # Caller may choose to retry without backup.
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
                self.logger.error("SSH upload verify mismatch: local=%s remote=%s remote_path=%s", local_sha, remote_sha, self.remote_path)
                self.finished.emit(False, "verify_failed")
                return
            self.logger.info("SSH upload verify ok: sha256=%s", remote_sha)

            cleanup_remote_backups(self.ip, self.port, self.user, self.pwd, self.remote_path)
            self.finished.emit(True, "")
        except Exception as e:
            self.finished.emit(False, str(e))

class _SshBackupWorker(QObject):
    finished = pyqtSignal(bool, object, str)  # ok, payload, error_text

    def __init__(self, action: str, ip: str, port: int, user: str, pwd: str, remote_path: str, backup_path: str | None = None):
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
        except Exception as e:
            self.finished.emit(False, None, str(e))

class KlipperConfigParser:
    def __init__(self, filepath):
        self.filepath = filepath
        self.raw_lines = []
        self.sections = {}

    def load(self):
        if not os.path.exists(self.filepath):
            return
            
        with open(self.filepath, 'r', encoding='utf-8') as f:
            self.raw_lines = f.readlines()
        
        self.sections.clear()
        current_section = None
        
        for i, line in enumerate(self.raw_lines):
            stripped = line.strip()
            
            if not stripped or stripped.startswith('#'):
                continue
                
            m = re.match(r'^\[(.+)\]$', stripped)
            if m:
                current_section = m.group(1)
                if current_section not in self.sections:
                    self.sections[current_section] = {}
                continue
            
            if current_section and ':' in stripped:
                if not stripped.startswith('#'):
                    parts = stripped.split(':', 1)
                    if len(parts) == 2:
                        key = parts[0].strip()
                        val_part = parts[1].split('#')[0].strip()
                        self.sections[current_section][key] = (val_part, i)

class ConfigEditor(QWidget):
    # Сигнал для уведомления внешней системы о завершении SSH операции
    ssh_operation_finished = pyqtSignal()
    ssh_download_succeeded = pyqtSignal(str)  # local_path

    def __init__(self):
        super().__init__()
        self.logger = get_logger(__name__)
        self.parser = None
        self.widgets = {}
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

        # Панель управления бэкапами (идёт первой)
        self.backup_group = QGroupBox("🧰 Бекапы printer.cfg")
        # Don't let this block steal vertical space.
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
        self.btn_save = QPushButton(S.get("config.btn_save")) # Локальное сохранение
        self.btn_save.setEnabled(False)
        
        # Кнопка сохранения на принтер
        self.btn_ssh_save = QPushButton("💾 Сохранить на принтер")
        self.btn_ssh_save.setEnabled(False)
        self.btn_ssh_save.setStyleSheet("background-color: #2d5a2d; color: white;")
        
        toolbar.addWidget(self.btn_load)
        toolbar.addWidget(self.btn_save)
        toolbar.addWidget(self.btn_ssh_save)
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
        self.btn_save.clicked.connect(self.save_changes_local)
        self.btn_ssh_save.clicked.connect(self.save_to_printer)
        self.btn_backup_refresh.clicked.connect(self._refresh_backups)
        self.btn_backup_create.clicked.connect(lambda: self._run_backup_action("create"))
        self.btn_backup_restore.clicked.connect(lambda: self._run_backup_action("restore"))
        self.btn_backup_delete.clicked.connect(lambda: self._run_backup_action("delete"))

    def set_ssh_config(self, config):
        self._ssh_config = config

    def load_from_ssh_data(self, ssh_data):
        """Вызывается главным окном при получении сигнала от LeftPanel"""
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
            "path": remote_path
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
                self.btn_ssh_save.setEnabled(True)
                self.status.setText(f"✅ Загружено с принтера ({ip})")
                self.ssh_download_succeeded.emit(local_path)

                # После первого успешного подключения — создаём "базовый" бекап, если наших бекапов ещё нет.
                # И всегда обновляем список бэкапов.
                if not self._auto_backup_done and self._ssh_config:
                    self._auto_backup_done = True
                    # `ensure` will schedule a refresh when it completes.
                    self._run_backup_action("ensure", silent=True)
                else:
                    self._refresh_backups()
            else:
                self.logger.error("SSH UI download failed: %s", error_text)
                QMessageBox.critical(self, "Ошибка SSH", "Не удалось скачать файл.\nПроверьте настройки подключения.\nПодробности в debug.log")
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
        self._ssh_backup_worker.finished.connect(lambda ok, payload, err: self._on_backup_action_finished(action, ok, payload, err, silent))
        self._ssh_backup_worker.finished.connect(self._ssh_backup_thread.quit)
        self._ssh_backup_thread.finished.connect(self._ssh_backup_thread.deleteLater)
        self._ssh_backup_thread.start()

    def _on_backup_action_finished(self, action: str, ok: bool, payload: object, error_text: str, silent: bool):
        should_refresh = False
        try:
            if action == "list" and ok:
                self.backup_list.clear()
                for p in (payload or []):
                    self.backup_list.addItem(str(p))
                self._update_backup_list_height()
                self.backup_status.setText(f"✅ Бекапов: {self.backup_list.count()} (лимит 5)")
                return

            if action in ("ensure", "create") and ok:
                self.backup_status.setText("✅ Готово")
                should_refresh = True

            if action in ("restore", "delete") and ok:
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
                # Defer refresh until after thread objects are cleared,
                # otherwise `_run_backup_action` may think an operation is still running.
                QTimer.singleShot(0, self._refresh_backups)

    def _update_backup_list_height(self, max_rows: int = 5):
        """
        Keep the list compact and show up to max_rows without a vertical scrollbar.
        """
        rows = min(self.backup_list.count(), max_rows)
        if rows <= 0:
            # reasonable default for an empty list (no scrollbar anyway)
            row_h = max(self.fontMetrics().height() + 6, 18)
            rows = 1
        else:
            row_h = self.backup_list.sizeHintForRow(0)
            if row_h <= 0:
                row_h = max(self.fontMetrics().height() + 6, 18)

        frame = self.backup_list.frameWidth() * 2
        height = frame + (row_h * rows) + 2  # small padding
        self.backup_list.setFixedHeight(height)

    def load_file(self, path=None):
        if not path:
            path, _ = QFileDialog.getOpenFileName(self, "Выберите printer.cfg", "", "Config Files (*.cfg);;All Files (*)")
        
        if not path or not os.path.exists(path):
            return

        self._process_loaded_file(path)
        self.btn_ssh_save.setEnabled(False)

    def _process_loaded_file(self, path):
        try:
            self.logger.info("Config processing start: path=%s", path)
            self.parser = KlipperConfigParser(path)
            self.parser.load()
            self._file_path = path
            self._build_ui()
            self.btn_save.setEnabled(False)
            self.status.setText(S.get("config.status_loaded", filename=os.path.basename(path)))
            self.logger.info(
                "Config processing done: sections=%s file_path=%s",
                len(self.parser.sections) if self.parser else None,
                self._file_path
            )
        except Exception as e:
            self.logger.exception("Config processing failed: path=%s error=%s", path, e)
            QMessageBox.critical(self, "Ошибка", S.get("config.msg_load_error", error=str(e)))

    def _build_ui(self):
        self.logger.debug(
            "Build UI start: sections_present=%s",
            list(self.parser.sections.keys())[:10] if self.parser and self.parser.sections else []
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

        target_sections = ["bed_mesh"]
        
        for sec_name in target_sections:
            if sec_name not in self.parser.sections:
                self.logger.warning("Build UI: section not found: %s", sec_name)
                continue
                
            sec_meta_key = f"config.sections.{sec_name}"
            sec_data = S.get(sec_meta_key, title=f"⚙️ [{sec_name}]")
            # `S.get` returns key string if the locale key is missing (or locale isn't loaded in packaged app).
            # Keep UI functional even without metadata.
            if isinstance(sec_data, str):
                self.logger.warning("Build UI: locale/meta missing for %s (got str)", sec_meta_key)
                sec_data = {"title": f"⚙️ [{sec_name}]", "fields": {}}
            fields_meta = sec_data.get("fields", {}) if isinstance(sec_data, dict) else {}
            
            group = QGroupBox(sec_data.get("title") if isinstance(sec_data, dict) else f"⚙️ [{sec_name}]")
            form = QFormLayout()
            group.setLayout(form)
            
            has_fields = False
            for key, (val, line_idx) in self.parser.sections[sec_name].items():
                meta = fields_meta.get(key)
                if not meta:
                    continue 
                
                label = meta.get('label', key)
                placeholder = meta.get('ph', '')
                tooltip = meta.get('tip', '')
                
                editor_widget: QWidget
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

    def save_changes_local(self):
        self._save_file_changes(silent=False)

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
            ip, port, user, remote_path, self._file_path
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
                self.logger.info("SSH UI upload success: remote_path=%s", self._ssh_config.get("path") if self._ssh_config else None)
                self.status.setText("✅ Сохранено на принтер")
                QMessageBox.information(self, "Успех", "Файл обновлен на принтере.\nБекап создан.")
                return

            if error_text == "backup_failed":
                reply = QMessageBox.question(
                    self,
                    "Предупреждение",
                    "Не удалось создать бекап на принтере. Продолжить сохранение без бекапа?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                if reply == QMessageBox.StandardButton.No:
                    self.status.setText("❌ Отменено")
                    return

                # Retry upload without backup in UI thread is still a bad idea; do it in a short worker.
                ip = self._ssh_config["ip"]
                port = self._ssh_config["port"]
                user = self._ssh_config["user"]
                pwd = self._ssh_config["password"]
                remote_path = self._ssh_config["path"]

                self.status.setText("⏳ Отправка файла...")
                self.repaint()

                self._ssh_upload_thread = QThread(self)
                self._ssh_upload_worker = _SshUploadWorker(self._file_path, ip, port, user, pwd, remote_path, create_backup=False)
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
            for (sec, key), w in self.widgets.items():
                new_val = self._get_widget_value(w).strip()
                new_val = self._normalize_bed_mesh_value(key, new_val, w if isinstance(w, QLineEdit) else None)
                
                if sec in self.parser.sections and key in self.parser.sections[sec]:
                    old_val, line_idx = self.parser.sections[sec][key]
                    
                    if new_val != old_val:
                        original_line = self.parser.raw_lines[line_idx]
                        indent = original_line[:len(original_line) - len(original_line.lstrip())]
                        self.parser.raw_lines[line_idx] = f"{indent}{key}: {new_val}\n"
                        changed = True

            if changed:
                with open(self._file_path, 'w', encoding='utf-8') as f:
                    f.writelines(self.parser.raw_lines)
                self.parser.load()
                
            self.btn_save.setEnabled(False)
            
            if not silent:
                self.status.setText(S.get("config.status_saved"))
                QMessageBox.information(self, S.get("config.msg_save_ok_title"), S.get("config.msg_save_ok_text"))
            
            return True
            
        except Exception as e:
            if not silent:
                QMessageBox.critical(self, "Ошибка", str(e))
            return False

    def _get_widget_value(self, w: QWidget) -> str:
        if isinstance(w, QLineEdit):
            return w.text()
        if isinstance(w, QComboBox):
            return w.currentText()
        return ""

    def _display_bed_mesh_value(self, key: str, raw_val: str) -> str:
        """
        UX helper: show single number in editor for pair values if they are identical.
        Example: "5,5" -> "5"
        """
        if key not in ("mesh_min", "mesh_max", "probe_count"):
            return raw_val
        if raw_val is None:
            return ""
        s = str(raw_val).strip()
        parts = [p.strip() for p in s.split(",")]
        if len(parts) != 2:
            return s
        a, b = parts[0], parts[1]
        if a == "" or b == "":
            return s
        if a == b:
            return a
        return s

    def _normalize_bed_mesh_value(self, key: str, value: str, le: QLineEdit | None = None) -> str:
        """
        UX helper: for pair values like mesh_min/mesh_max/probe_count allow entering single number (e.g. "5")
        and write it as "5,5" in config.
        """
        if key not in ("mesh_min", "mesh_max", "probe_count"):
            return value
        v = (value or "").strip()
        if not v:
            return v
        if "," in v:
            return v
        # If user entered a single number, duplicate it.
        # For probe_count prefer integers.
        num_re = r"\d+" if key == "probe_count" else r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)"
        if re.fullmatch(num_re, v):
            normalized = f"{v},{v}"
            return normalized
        return v

    def load_from_path(self, path):
        self.load_file(path)