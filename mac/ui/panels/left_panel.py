from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class LeftPanel(QWidget):
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
        self.input_ip.textChanged.connect(lambda text: self.setting_updated.emit("ssh_ip", text))
        layout.addWidget(self.input_ip)

        self.btn_ssh = QPushButton("🌐 Загрузить по SSH")
        self.btn_ssh.clicked.connect(self._request_ssh_download)
        layout.addWidget(self.btn_ssh)

        self.chk_advanced = QCheckBox("⚙️ Расширенные настройки")
        self.chk_advanced.setChecked(False)
        self.chk_advanced.stateChanged.connect(self._toggle_advanced)
        layout.addWidget(self.chk_advanced)

        self.adv_group = QGroupBox()
        self.adv_group.setVisible(self.chk_advanced.isChecked())
        adv_layout = QVBoxLayout(self.adv_group)
        adv_layout.setContentsMargins(5, 5, 5, 5)

        self.adv_fields = {}
        fields_cfg = [
            ("ssh_port", "Порт", initial_settings.get("ssh_port", "2222")),
            ("ssh_user", "Логин", initial_settings.get("ssh_user", "root")),
            ("ssh_pass", "Пароль", initial_settings.get("ssh_pass", "rockchip")),
            ("ssh_path", "Путь к файлу", initial_settings.get("ssh_path", "/userdata/app/gk/printer.cfg")),
        ]

        for key, label_text, default in fields_cfg:
            row = QHBoxLayout()
            label = QLabel(label_text + ":")
            label.setFixedWidth(80)
            row.addWidget(label)
            line = QLineEdit(default)
            if key == "ssh_pass":
                line.setEchoMode(QLineEdit.EchoMode.Password)
            line.textChanged.connect(lambda text, setting_key=key: self.setting_updated.emit(setting_key, text))
            row.addWidget(line)
            adv_layout.addLayout(row)
            self.adv_fields[key] = line

        layout.addWidget(self.adv_group)

        layout.addSpacing(15)
        self.btn_log = QPushButton("📋 Открыть лог")
        self.btn_log.clicked.connect(self._open_log)
        layout.addWidget(self.btn_log)

        layout.addStretch()

    def _request_ssh_download(self):
        data = {
            "ip": self.input_ip.text(),
            "port": self.adv_fields["ssh_port"].text(),
            "user": self.adv_fields["ssh_user"].text(),
            "password": self.adv_fields["ssh_pass"].text(),
            "path": self.adv_fields["ssh_path"].text(),
        }
        self.ssh_download_requested.emit(data)
        self.btn_ssh.setEnabled(False)
        self.btn_ssh.setText("⏳ Загрузка...")

    def reset_ssh_button(self):
        self.btn_ssh.setEnabled(True)
        self.btn_ssh.setText("🌐 Загрузить по SSH")

    def _toggle_advanced(self, state):
        is_checked = state == 2
        self.adv_group.setVisible(is_checked)
        self.advanced_toggled.emit(is_checked)

    def _open_log(self):
        from utils.logger import open_log_file

        open_log_file()
