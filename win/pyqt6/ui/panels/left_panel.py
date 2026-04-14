import os
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QLabel, QFileDialog, QLineEdit, QHBoxLayout
from PyQt6.QtCore import pyqtSignal

class LeftPanel(QWidget):
    # Сигналы для разных действий
    file_selected = pyqtSignal(str)
    ssh_requested = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        title = QLabel("🔧 Управление")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(title)

        # --- Блок выбора файла ---
        lbl_file = QLabel("Локальный файл:")
        layout.addWidget(lbl_file)
        
        self.btn_open = QPushButton("📂 Выбрать конфиг (файл)")
        self.btn_open.clicked.connect(self._open_file)
        layout.addWidget(self.btn_open)

        layout.addSpacing(20)

        # --- Блок SSH ---
        lbl_ssh = QLabel("Загрузка с принтера (SSH):")
        layout.addWidget(lbl_ssh)

        self.input_ip = QLineEdit()
        self.input_ip.setPlaceholderText("Введите IP адрес принтера...")
        self.input_ip.setText("192.168.") # Подсказка
        layout.addWidget(self.input_ip)

        self.btn_ssh = QPushButton("🌐 Загрузить по SSH")
        self.btn_ssh.clicked.connect(self._do_ssh_download)
        layout.addWidget(self.btn_ssh)

        layout.addStretch()

    def _open_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Выберите конфиг Klipper", "", "Config Files (*.cfg *.conf);;All Files (*)"
        )
        if path:
            self.file_selected.emit(path)

    def _do_ssh_download(self):
        ip = self.input_ip.text()
        if ip:
            self.btn_ssh.setEnabled(False)
            self.btn_ssh.setText("⏳ Подключение...")
            self.ssh_requested.emit(ip)
        else:
            self.input_ip.setStyleSheet("background-color: #ffcccc;") # Красная подсветка если пусто