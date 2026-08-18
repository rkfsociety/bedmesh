import os
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QPushButton, QLabel,
                             QLineEdit, QHBoxLayout, QGroupBox, QMessageBox)
from PyQt6.QtCore import pyqtSignal, QObject, QThread, QTimer
from ui.components.toggle_switch import ToggleSwitch
from core.ssh_client import (
    install_persistent_ssh, install_web_panel,
    uninstall_persistent_ssh, uninstall_web_panel,
    check_persistent_status,
)


class _PersistWorker(QObject):
    """Фоновая операция автозапуска: статус / установка / откат (не вешает GUI)."""
    # op, ok, payload (для status — dict, иначе None), error_text
    finished = pyqtSignal(str, bool, object, str)

    def __init__(self, op: str, ssh_data: dict):
        super().__init__()
        self.op = op  # status | install_ssh | install_panel | uninstall_ssh | uninstall_panel
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

            if self.op == "status":
                status = check_persistent_status(ip, port, user, pwd)
                self.finished.emit("status", status is not None, status,
                                   "" if status is not None else "Нет связи с принтером")
                return

            if self.op == "install_ssh":
                ok = install_persistent_ssh(ip, port, user, pwd)
            elif self.op in ("install_panel", "update_panel"):
                ok = install_web_panel(ip, port, user, pwd)
            elif self.op == "uninstall_ssh":
                ok = uninstall_persistent_ssh(ip, port, user, pwd)
            elif self.op == "uninstall_panel":
                ok = uninstall_web_panel(ip, port, user, pwd)
            else:
                ok = False
            self.finished.emit(self.op, ok, None,
                               "" if ok else "Операция не выполнена. Подробности в debug.log")
        except Exception as e:
            self.finished.emit(self.op, False, None, str(e))


class LeftPanel(QWidget):
    # Отправляем словарь с настройками SSH
    ssh_download_requested = pyqtSignal(dict)
    setting_updated = pyqtSignal(str, str)
    advanced_toggled = pyqtSignal(bool)

    def __init__(self, initial_settings: dict):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        title = QLabel("🔧 Управление")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(title)
        layout.addSpacing(10)

        self._pending_setting_updates: dict[str, str] = {}
        self._settings_save_timer = QTimer(self)
        self._settings_save_timer.setSingleShot(True)
        self._settings_save_timer.setInterval(350)
        self._settings_save_timer.timeout.connect(self._flush_setting_updates)

        lbl_ip = QLabel("IP адрес принтера:")
        layout.addWidget(lbl_ip)
        self.input_ip = QLineEdit(initial_settings.get("ssh_ip", "192.168."))
        self.input_ip.textChanged.connect(lambda t: self._queue_setting_update("ssh_ip", t))
        layout.addWidget(self.input_ip)

        self.btn_ssh = QPushButton("🌐 Загрузить по SSH")
        self.btn_ssh.setObjectName("primaryButton")
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

        self.adv_group = QGroupBox("Параметры подключения и сервисы")
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
            line.textChanged.connect(lambda t, k=key: self._queue_setting_update(k, t))
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
        self.btn_persist_ssh.clicked.connect(lambda: self._on_persist_clicked("ssh"))
        adv_layout.addWidget(self.btn_persist_ssh)

        self.btn_web_panel = QPushButton("📊 Установить веб-панель")
        self.btn_web_panel.setToolTip(
            "Скачивает свежий gkbridge с GitHub, заливает в /useremain и прописывает автозапуск.\n"
            "Веб-панель статуса печати становится доступна на http://<ip>:8088/"
        )
        self.btn_web_panel.clicked.connect(lambda: self._on_persist_clicked("panel"))
        adv_layout.addWidget(self.btn_web_panel)

        # Принудительное обновление: свежий бинарник с GitHub (не из бандла exe).
        self.btn_web_update = QPushButton("🔄 Обновить веб-панель")
        self.btn_web_update.setToolTip(
            "Скачивает актуальный gkbridge с GitHub, заливает на принтер и перезапускает панель.\n"
            "Если GitHub недоступен — использует бинарник, встроенный в программу."
        )
        self.btn_web_update.setVisible(False)
        self.btn_web_update.clicked.connect(self._on_web_update_clicked)
        adv_layout.addWidget(self.btn_web_update)

        self.persist_status_lbl = QLabel("Статус: неизвестно (загрузите конфиг по SSH)")
        self.persist_status_lbl.setStyleSheet("font-size: 11px; color: #888;")
        self.persist_status_lbl.setWordWrap(True)
        adv_layout.addWidget(self.persist_status_lbl)

        layout.addWidget(self.adv_group)

        # Состояние фонового потока и текущая установка на принтере.
        self._persist_thread = None
        self._persist_worker = None
        self._ssh_installed = False
        self._panel_installed = False
        
        layout.addSpacing(15)
        self.btn_log = QPushButton("📋 Открыть лог")
        self.btn_log.clicked.connect(self._open_log)
        layout.addWidget(self.btn_log)
        
        layout.addStretch()

    def _queue_setting_update(self, key: str, value: str) -> None:
        """Откладывает сохранение, пока пользователь продолжает печатать."""
        self._pending_setting_updates[key] = value
        self._settings_save_timer.start()

    def _flush_setting_updates(self) -> None:
        pending = self._pending_setting_updates
        self._pending_setting_updates = {}
        for key, value in pending.items():
            self.setting_updated.emit(key, value)

    def flush_pending_settings(self) -> None:
        """Синхронно отправляет отложенные изменения перед закрытием приложения."""
        if self._settings_save_timer.isActive():
            self._settings_save_timer.stop()
        self._flush_setting_updates()

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

    def refresh_persist_status(self):
        """Проверяет, что установлено на принтере, и обновляет кнопки. Вызывать после SSH-загрузки."""
        if self._persist_thread and self._persist_thread.isRunning():
            return
        ssh_data = self._collect_ssh_data()
        if not ssh_data.get("ip"):
            return
        self.persist_status_lbl.setText("Статус: проверка...")
        self._start_persist_op("status", ssh_data)

    def _on_persist_clicked(self, target: str):
        """target: 'ssh' | 'panel'. Установить или откатить — в зависимости от текущего статуса."""
        if self._persist_thread and self._persist_thread.isRunning():
            QMessageBox.information(self, "Автозапуск", "Операция уже выполняется, подождите.")
            return

        ssh_data = self._collect_ssh_data()
        if not ssh_data.get("ip"):
            QMessageBox.warning(self, "Автозапуск", "Укажите IP адрес принтера.")
            return

        installed = self._ssh_installed if target == "ssh" else self._panel_installed
        name = "постоянный SSH" if target == "ssh" else "веб-панель"

        if installed:
            extra = ("\n\nЗапущенный dropbear не будет остановлен (это оборвало бы текущее "
                     "подключение) — SSH исчезнет только после перезагрузки принтера."
                     if target == "ssh" else "")
            reply = QMessageBox.question(
                self, "Откатить?",
                f"Убрать {name} с принтера?{extra}",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                return
            op = "uninstall_ssh" if target == "ssh" else "uninstall_panel"
        else:
            op = "install_ssh" if target == "ssh" else "install_panel"

        self._start_persist_op(op, ssh_data)

    def _on_web_update_clicked(self):
        """Принудительное обновление панели свежим бинарником из программы."""
        if self._persist_thread and self._persist_thread.isRunning():
            QMessageBox.information(self, "Автозапуск", "Операция уже выполняется, подождите.")
            return
        ssh_data = self._collect_ssh_data()
        if not ssh_data.get("ip"):
            QMessageBox.warning(self, "Автозапуск", "Укажите IP адрес принтера.")
            return
        self._start_persist_op("update_panel", ssh_data)

    def _start_persist_op(self, op: str, ssh_data: dict):
        busy_text = {
            "status": None,
            "install_ssh": ("ssh", "⏳ Установка SSH..."),
            "uninstall_ssh": ("ssh", "⏳ Откат SSH..."),
            "install_panel": ("panel", "⏳ Установка панели..."),
            "uninstall_panel": ("panel", "⏳ Откат панели..."),
            "update_panel": ("update", "⏳ Обновление панели..."),
        }.get(op)

        self._set_persist_buttons_enabled(False)
        if busy_text:
            which, text = busy_text
            btn = {"ssh": self.btn_persist_ssh, "panel": self.btn_web_panel,
                   "update": self.btn_web_update}[which]
            btn.setText(text)

        self._persist_thread = QThread(self)
        self._persist_worker = _PersistWorker(op, ssh_data)
        self._persist_worker.moveToThread(self._persist_thread)
        self._persist_thread.started.connect(self._persist_worker.run)
        self._persist_worker.finished.connect(self._on_persist_finished)
        self._persist_worker.finished.connect(self._persist_thread.quit)
        self._persist_thread.finished.connect(self._persist_thread.deleteLater)
        self._persist_thread.start()

    def _on_persist_finished(self, op: str, ok: bool, payload: object, error_text: str):
        self._persist_worker = None
        self._persist_thread = None

        if op == "status":
            if ok and isinstance(payload, dict):
                self._ssh_installed = bool(payload.get("ssh_installed"))
                self._panel_installed = bool(payload.get("panel_installed"))
                self._apply_persist_status_label(payload)
            else:
                self.persist_status_lbl.setText("Статус: не удалось проверить (нет связи)")
            self._update_persist_buttons()
            self._set_persist_buttons_enabled(True)
            return

        # install_* / uninstall_*
        ip = self.input_ip.text().strip()
        if ok:
            if op == "install_ssh":
                msg = ("Постоянный SSH установлен.\n\n"
                       "Можно вынуть загрузочную флешку и перезагрузить принтер — "
                       f"SSH (порт 2222) поднимется сам.\n\nАдрес: {ip}:2222")
            elif op == "install_panel":
                msg = ("Веб-панель установлена и запущена.\n\n"
                       f"Откройте в браузере: http://{ip}:8088/\n\n"
                       "После перезагрузки принтера панель поднимется автоматически.")
            elif op == "uninstall_ssh":
                msg = ("Постоянный SSH убран. После перезагрузки принтера без флешки "
                       "SSH больше не поднимется.")
            elif op == "update_panel":
                msg = ("Веб-панель обновлена до версии из программы и перезапущена.\n\n"
                       f"Откройте/обновите в браузере: http://{ip}:8088/")
            else:
                msg = "Веб-панель убрана и остановлена."
            QMessageBox.information(self, "Готово", msg)
        else:
            QMessageBox.critical(self, "Ошибка", error_text or "Не удалось выполнить операцию.")

        # Перепроверяем реальное состояние и обновляем кнопки.
        self._update_persist_buttons()
        QTimer.singleShot(0, self.refresh_persist_status)

    def _apply_persist_status_label(self, st: dict):
        ssh_txt = "✅ SSH" if st.get("ssh_installed") else "⛔ SSH"
        panel_txt = "✅ панель" if st.get("panel_installed") else "⛔ панель"
        note = ""
        # Артефакт есть, а хука нет — типично после OTA-обновления прошивки.
        if (st.get("ssh_artifact") or st.get("panel_artifact")) and not st.get("hook"):
            note = "  ⚠️ автозапуск слетел (OTA?) — переустановите"
        self.persist_status_lbl.setText(f"Статус: {ssh_txt}, {panel_txt}{note}")

    def _update_persist_buttons(self):
        self.btn_persist_ssh.setText(
            "🔓 Убрать постоянный SSH" if self._ssh_installed else "🔒 Установить постоянный SSH"
        )
        self.btn_web_panel.setText(
            "🗑 Убрать веб-панель" if self._panel_installed else "📊 Установить веб-панель"
        )
        # Кнопку принудительного обновления показываем только когда панель установлена
        # (при «не установлено» эту роль выполняет сама кнопка установки).
        self.btn_web_update.setText("🔄 Обновить веб-панель")
        self.btn_web_update.setVisible(self._panel_installed)

    def _set_persist_buttons_enabled(self, enabled: bool):
        self.btn_persist_ssh.setEnabled(enabled)
        self.btn_web_panel.setEnabled(enabled)
        self.btn_web_update.setEnabled(enabled)

    def _open_log(self):
        from utils.logger import open_log_file
        open_log_file()
