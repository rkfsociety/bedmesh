import os
import re
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                             QLabel, QFileDialog, QScrollArea, QFormLayout,
                             QGroupBox, QLineEdit, QMessageBox)
from PyQt6.QtCore import Qt, pyqtSignal, QObject, QThread
from utils.strings import S
from utils.logger import get_logger
from core.ssh_client import (
    download_cfg_via_ssh, 
    upload_cfg_via_ssh, 
    create_remote_backup,
    cleanup_remote_backups
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
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)

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
            else:
                self.logger.error("SSH UI download failed: %s", error_text)
                QMessageBox.critical(self, "Ошибка SSH", "Не удалось скачать файл.\nПроверьте настройки подключения.\nПодробности в debug.log")
                self.status.setText("❌ Ошибка загрузки")
        finally:
            self._ssh_worker = None
            self._ssh_thread = None
            self.ssh_operation_finished.emit()

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
            fields_meta = sec_data.get("fields", {})
            
            group = QGroupBox(sec_data.get("title"))
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
                
                le = QLineEdit(val)
                le.setStyleSheet("background: #2b2b2b; color: #d4d4d4; border: 1px solid #444; padding: 4px;")
                le.setPlaceholderText(placeholder)
                le.setToolTip(tooltip)
                
                le.textChanged.connect(self._on_changed)
                
                form.addRow(f"{label}:", le)
                self.widgets[(sec_name, key)] = le
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
        
        self.status.setText("⏳ Создание бекапа на принтере...")
        self.repaint()

        backup_success = create_remote_backup(ip, port, user, pwd, remote_path)
        
        if not backup_success:
            reply = QMessageBox.question(self, "Предупреждение", 
                                         "Не удалось создать бекап на принтере. Продолжить?",
                                         QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.No:
                self.status.setText("❌ Отменено")
                self.ssh_operation_finished.emit()
                return

        self.status.setText("⏳ Отправка файла...")
        self.repaint()

        success = upload_cfg_via_ssh(self._file_path, ip, port, user, pwd, remote_path)
        
        if success:
            self.logger.info("SSH UI upload success: remote_path=%s", remote_path)
            cleanup_remote_backups(ip, port, user, pwd, remote_path)
            self.status.setText("✅ Сохранено на принтер")
            QMessageBox.information(self, "Успех", "Файл обновлен на принтере.\nБекап создан.")
        else:
            self.logger.error("SSH UI upload failed (see previous exception details)")
            QMessageBox.critical(self, "Ошибка", "Не удалось загрузить файл на принтер.")
            self.status.setText("❌ Ошибка отправки")
        
        self.ssh_operation_finished.emit()

    def _save_file_changes(self, silent=False):
        if not self.parser or not self._file_path: 
            return False
        
        try:
            changed = False
            for (sec, key), le in self.widgets.items():
                new_val = le.text().strip()
                
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

    def load_from_path(self, path):
        self.load_file(path)