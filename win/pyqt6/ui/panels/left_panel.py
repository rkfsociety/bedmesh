import os
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QPushButton, QLabel,
                             QLineEdit, QHBoxLayout, QGroupBox, QMessageBox)
from PyQt6.QtCore import pyqtSignal, QObject, QThread
from ui.components.toggle_switch import ToggleSwitch
from core.ssh_client import install_persistent_ssh, install_web_panel


class _PersistInstallWorker(QObject):
    """Фоновая установка постоянного SSH или веб-панели (не вешает GUI)."""
    finished = pyqtSignal(bool, str)  # ok, error_text

    def __init__(self, action: str, ssh_data: dict):
        super().__init__()
        self.action = action  # "ssh" | "panel"
        self.ssh_data = ssh_data

    def run(self):
        try:
            ip = self.ssh_data.get("ip")
            try:
                port = int(self.ssh_data.get("port", 2222))
            except (TypeError, ValueError):
                port = 2222
            user = self.ssh_data.get("user", "root")
            pwd = self.ssh_data.get("password", "")
            if self.action == "ssh":
                ok = install_persistent_ssh(ip, port, user, pwd)
            else:
                ok = install_web_panel(ip, port, user, pwd)
            self.finished.emit(ok, "" if ok else "Операция не выполнена. Подробности в debug.log")
        except Exception as e:
            self.finished.emit(False, str(e))


class LeftPanel(QWidget):
    # Отправляем словарь с настройками SSH
    ssh_download_requested = pyqtSignal(dict)
    setting_updated = pyqtSignal(str, str)
    advanced_toggled = pyqtSignal(bool)

    def __init__(self, initial_settings: dict):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        title = QLabel("🔧 Управление")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(title)
        layout.addSpacing(10)

        lbl_ip = QLabel("IP адрес принтера:")
        layout.addWidget(lbl_ip)
        self.input_ip = QLineEdit(initial_settings.get("ssh_ip", "192.168."))
        self.input_ip.textChanged.connect(lambda t: self.setting_updated.emit("ssh_ip", t))
        layout.addWidget(self.input_ip)

        self.btn_ssh = QPushButton("🌐 Загрузить по SSH")
        self.btn_ssh.clicked.connect(self._request_ssh_download)
        layout.addWidget(self.btn_ssh)

        toggle_row = QHBoxLayout()
        self.chk_advanced = ToggleSwitch(checked=False)
        self.chk_advanced.toggled.connect(self._toggle_advanced)
        toggle_lbl = QLabel("⚙️ Расширенные настройки")
        toggle_lbl.setStyleSheet("font-size: 13px;")
        toggle_row.addWidget(self.chk_advanced)
        toggle_row.addSpacing(8)
        toggle_row.addWidget(toggle_lbl)
        toggle_row.addStretch()
        layout.addLayout(toggle_row)

        self.adv_group = QGroupBox()
        self.adv_group.setVisible(self.chk_advanced.isChecked())
        adv_layout = QVBoxLayout(self.adv_group)
        adv_layout.setContentsMargins(5, 5, 5, 5)

        self.adv_fields = {}
        fields_cfg = [
            ("ssh_port", "Порт", initial_settings.get("ssh_port", "2222")),
            ("ssh_user", "Логин", initial_settings.get("ssh_user", "root")),
            ("ssh_pass", "Пароль", initial_settings.get("ssh_pass", "rockchip")),
            ("ssh_path", "Путь к файлу", initial_settings.get("ssh_path", "/userdata/app/gk/printer.cfg"))
        ]

        for key, label_text, default in fields_cfg:
            row = QHBoxLayout()
            lbl = QLabel(label_text + ":")
            lbl.setFixedWidth(80)
            row.addWidget(lbl)
            line = QLineEdit(default)
            if key == "ssh_pass":
                line.setEchoMode(QLineEdit.EchoMode.Password)
            line.textChanged.connect(lambda t, k=key: self.setting_updated.emit(k, t))
            row.addWidget(line)
            adv_layout.addLayout(row)
            self.adv_fields[key] = line

        # Постоянный автозапуск на принтере (две независимые установки).
        adv_layout.addSpacing(8)
        persist_lbl = QLabel("Автозапуск на принтере (без флешки):")
        persist_lbl.setStyleSheet("font-size: 12px; color: #aaa;")
        adv_layout.addWidget(persist_lbl)

        self.btn_persist_ssh = QPushButton("🔒 Установить постоянный SSH")
        self.btn_persist_ssh.setToolTip(
            "Разворачивает dropbear в /useremain и прописывает автозапуск в run.sh.\n"
            "После этого SSH (порт 2222) поднимается сам, без загрузочной флешки."
        )
        self.btn_persist_ssh.clicked.connect(lambda: self._start_persist_install("ssh"))
        adv_layout.addWidget(self.btn_persist_ssh)

        self.btn_web_panel = QPushButton("📊 Установить веб-панель")
        self.btn_web_panel.setToolTip(
            "Заливает gkbridge в /useremain и прописывает автозапуск.\n"
            "Веб-панель статуса печати становится доступна на http://<ip>:8088/"
        )
        self.btn_web_panel.clicked.connect(lambda: self._start_persist_install("panel"))
        adv_layout.addWidget(self.btn_web_panel)

        layout.addWidget(self.adv_group)

        # Состояние фонового потока установки.
        self._persist_thread = None
        self._persist_worker = None
        
        layout.addSpacing(15)
        self.btn_log = QPushButton("📋 Открыть лог")
        self.btn_log.clicked.connect(self._open_log)
        layout.addWidget(self.btn_log)
        
        layout.addStretch()

    def _request_ssh_download(self):
        """Собирает данные из полей и отправляет сигнал"""
        data = {
            "ip": self.input_ip.text(),
            "port": self.adv_fields["ssh_port"].text(),
            "user": self.adv_fields["ssh_user"].text(),
            "password": self.adv_fields["ssh_pass"].text(),
            "path": self.adv_fields["ssh_path"].text()
        }
        self.ssh_download_requested.emit(data)
        # Блокируем кнопку до завершения операции
        self.btn_ssh.setEnabled(False)
        self.btn_ssh.setText("⏳ Загрузка...")

    def reset_ssh_button(self):
        """Сброс состояния кнопки после завершения операции"""
        self.btn_ssh.setEnabled(True)
        self.btn_ssh.setText("🌐 Загрузить по SSH")

    def _toggle_advanced(self, is_checked: bool):
        self.adv_group.setVisible(is_checked)
        self.advanced_toggled.emit(is_checked)

    def _collect_ssh_data(self) -> dict:
        return {
            "ip": self.input_ip.text(),
            "port": self.adv_fields["ssh_port"].text(),
            "user": self.adv_fields["ssh_user"].text(),
            "password": self.adv_fields["ssh_pass"].text(),
            "path": self.adv_fields["ssh_path"].text(),
        }

    def _start_persist_install(self, action: str):
        """Запускает установку постоянного SSH (action='ssh') или панели ('panel')."""
        if self._persist_thread and self._persist_thread.isRunning():
            QMessageBox.information(self, "Установка", "Операция уже выполняется, подождите.")
            return

        ssh_data = self._collect_ssh_data()
        if not ssh_data.get("ip"):
            QMessageBox.warning(self, "Установка", "Укажите IP адрес принтера.")
            return

        title = "постоянного SSH" if action == "ssh" else "веб-панели"
        self._set_persist_buttons_enabled(False)
        if action == "ssh":
            self.btn_persist_ssh.setText("⏳ Установка SSH...")
        else:
            self.btn_web_panel.setText("⏳ Установка панели...")

        self._persist_thread = QThread(self)
        self._persist_worker = _PersistInstallWorker(action, ssh_data)
        self._persist_worker.moveToThread(self._persist_thread)
        self._persist_thread.started.connect(self._persist_worker.run)
        self._persist_worker.finished.connect(
            lambda ok, err, a=action: self._on_persist_finished(a, ok, err)
        )
        self._persist_worker.finished.connect(self._persist_thread.quit)
        self._persist_thread.finished.connect(self._persist_thread.deleteLater)
        self._persist_thread.start()

    def _on_persist_finished(self, action: str, ok: bool, error_text: str):
        self._persist_worker = None
        self._persist_thread = None
        self._reset_persist_buttons()
        self._set_persist_buttons_enabled(True)

        ip = self.input_ip.text().strip()
        if ok:
            if action == "ssh":
                msg = ("Постоянный SSH установлен.\n\n"
                       "Можно вынуть загрузочную флешку и перезагрузить принтер — "
                       f"SSH (порт 2222) поднимется сам.\n\nАдрес: {ip}:2222")
            else:
                msg = ("Веб-панель установлена и запущена.\n\n"
                       f"Откройте в браузере: http://{ip}:8088/\n\n"
                       "После перезагрузки принтера панель поднимется автоматически.")
            QMessageBox.information(self, "Готово", msg)
        else:
            QMessageBox.critical(self, "Ошибка установки", error_text or "Не удалось выполнить установку.")

    def _set_persist_buttons_enabled(self, enabled: bool):
        self.btn_persist_ssh.setEnabled(enabled)
        self.btn_web_panel.setEnabled(enabled)

    def _reset_persist_buttons(self):
        self.btn_persist_ssh.setText("🔒 Установить постоянный SSH")
        self.btn_web_panel.setText("📊 Установить веб-панель")

    def _open_log(self):
        from utils.logger import open_log_file
        open_log_file()