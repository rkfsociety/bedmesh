import os
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QLabel, QFileDialog
from PyQt6.QtCore import pyqtSignal

class LeftPanel(QWidget):
    config_loaded = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        title = QLabel("🔧 Управление")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(title)

        self.path_label = QLabel("Файл не выбран")
        self.path_label.setWordWrap(True)
        layout.addWidget(self.path_label)

        self.btn_open = QPushButton("📂 Выбрать конфиг")
        self.btn_open.clicked.connect(self._open_file)
        layout.addWidget(self.btn_open)

        layout.addStretch()

    def _open_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Выберите конфиг Klipper", "", "Config Files (*.cfg *.conf *.ini);;All Files (*)"
        )
        if path:
            filename = os.path.basename(path)
            self.path_label.setText(f"📄 {filename}")
            self.config_loaded.emit(path)