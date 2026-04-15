import os
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QPlainTextEdit, QLabel, QFileDialog
from PyQt6.QtCore import Qt

class ConfigEditor(QWidget):
    def __init__(self):
        super().__init__()
        self._setup_ui()
        self._file_path = None

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)

        toolbar = QHBoxLayout()
        self.btn_load = QPushButton("📂 Загрузить файл")
        self.btn_save = QPushButton("💾 Сохранить")
        self.btn_save.setEnabled(False)
        self.status = QLabel("Готов к работе")
        self.status.setStyleSheet("color: #888;")

        toolbar.addWidget(self.btn_load)
        toolbar.addWidget(self.btn_save)
        toolbar.addStretch()
        toolbar.addWidget(self.status)
        layout.addLayout(toolbar)

        self.editor = QPlainTextEdit()
        self.editor.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.editor.setTabStopDistance(40)
        self.editor.setStyleSheet("""
            QPlainTextEdit {
                background: #1e1e1e; color: #d4d4d4;
                font-family: Consolas, monospace; font-size: 13px;
                border: 1px solid #444; border-radius: 4px; padding: 8px;
            }
        """)
        self.editor.textChanged.connect(self._on_changed)
        layout.addWidget(self.editor)

        self.btn_load.clicked.connect(self.load_file)
        self.btn_save.clicked.connect(self.save_file)

    def load_file(self, path: str = None):
        if not path:
            path, _ = QFileDialog.getOpenFileName(self, "Выберите printer.cfg", "", "Config Files (*.cfg);;All Files (*)")
        if not path or not os.path.exists(path):
            return

        try:
            with open(path, 'r', encoding='utf-8') as f:
                self.editor.setPlainText(f.read())
            self._file_path = path
            self.btn_save.setEnabled(False)
            self.status.setText(f"✅ Загружено: {os.path.basename(path)}")
        except Exception as e:
            self.status.setText(f"❌ Ошибка: {e}")

    def save_file(self):
        if not self._file_path:
            path, _ = QFileDialog.getSaveFileName(self, "Сохранить как", "", "Config Files (*.cfg)")
            if not path: return
            self._file_path = path

        try:
            with open(self._file_path, 'w', encoding='utf-8') as f:
                f.write(self.editor.toPlainText())
            self.btn_save.setEnabled(False)
            self.status.setText("💾 Успешно сохранено")
        except Exception as e:
            self.status.setText(f"❌ Ошибка: {e}")

    def _on_changed(self):
        self.btn_save.setEnabled(True)

    def load_from_path(self, path: str):
        """Загрузка извне (для связи с левой панелью или SSH)"""
        self.load_file(path)