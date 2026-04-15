import os
import re
import json
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                             QLabel, QFileDialog, QScrollArea, QFormLayout,
                             QGroupBox, QLineEdit, QMessageBox)
from PyQt6.QtCore import Qt

class KlipperConfigParser:
    """Парсер, сохраняющий номера строк для безопасной перезаписи"""
    def __init__(self, filepath):
        self.filepath = filepath
        self.raw_lines = []
        self.sections = {}

    def load(self):
        with open(self.filepath, 'r', encoding='utf-8') as f:
            self.raw_lines = f.readlines()
        self.sections.clear()
        current_section = None
        for i, line in enumerate(self.raw_lines):
            stripped = line.strip()
            m = re.match(r'^\[(.+)\]$', stripped)
            if m:
                current_section = m.group(1)
                self.sections[current_section] = {}
            elif current_section and ':' in stripped and not stripped.startswith('#'):
                k, _, v = stripped.partition(':')
                k, v = k.strip(), v.split('#')[0].strip()
                self.sections[current_section][k] = (v, i)

class ConfigEditor(QWidget):
    def __init__(self):
        super().__init__()
        self.parser = None
        self.widgets = {}
        self._file_path = None
        self.labels = self._load_labels()
        self._setup_ui()

    def _load_labels(self):
        json_path = os.path.join(os.path.dirname(__file__), 'labels.json')
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return {"ui": {}, "sections": {}}

    def _setup_ui(self):
        ui = self.labels.get("ui", {})
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)

        toolbar = QHBoxLayout()
        self.btn_load = QPushButton(ui.get("btn_load", "📂 Загрузить файл"))
        self.btn_save = QPushButton(ui.get("btn_save", "💾 Сохранить изменения"))
        self.btn_save.setEnabled(False)
        self.status = QLabel(ui.get("status_ready", "Готов к работе"))
        self.status.setStyleSheet("color: #888;")
        toolbar.addWidget(self.btn_load)
        toolbar.addWidget(self.btn_save)
        toolbar.addStretch()
        toolbar.addWidget(self.status)
        layout.addLayout(toolbar)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self.container = QWidget()
        self.container_layout = QVBoxLayout(self.container)
        self.container_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        scroll.setWidget(self.container)
        layout.addWidget(scroll)

        self.btn_load.clicked.connect(self.load_file)
        self.btn_save.clicked.connect(self.save_changes)

    def load_file(self, path: str = None):
        if not path:
            path, _ = QFileDialog.getOpenFileName(self, "Выберите printer.cfg", "", "Config Files (*.cfg);;All Files (*)")
        if not path or not os.path.exists(path):
            return

        try:
            self.parser = KlipperConfigParser(path)
            self.parser.load()
            self._file_path = path
            self._build_ui()
            self.btn_save.setEnabled(False)
            self.status.setText(self.labels.get("ui", {}).get("status_loaded", "✅ Загружено: {}").format(os.path.basename(path)))
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", self.labels.get("ui", {}).get("msg_load_error", "Ошибка:\n{}").format(e))

    def _build_ui(self):
        while self.container_layout.count():
            self.container_layout.itemAt(0).widget().deleteLater()
        self.widgets.clear()

        sections = self.labels.get("sections", {})
        for sec_name, sec_data in sections.items():
            if sec_name not in self.parser.sections:
                self.status.setText(self.labels.get("ui", {}).get("status_section_missing", "⚠️ Секция [{}] не найдена").format(sec_name))
                continue

            group = QGroupBox(sec_data.get("title", f"[{sec_name}]"))
            form = QFormLayout()
            group.setLayout(form)

            for key, field in sec_data.get("fields", {}).items():
                if key not in self.parser.sections[sec_name]:
                    continue
                val, _ = self.parser.sections[sec_name][key]
                le = QLineEdit(val)
                le.setStyleSheet("background: #2b2b2b; color: #d4d4d4; border: 1px solid #444; padding: 4px;")
                le.textChanged.connect(self._on_changed)
                le.setPlaceholderText(field.get("placeholder", ""))
                le.setToolTip(field.get("desc", ""))
                form.addRow(f"{field.get('label', key)}:", le)
                self.widgets[(sec_name, key)] = le

            self.container_layout.addWidget(group)
        self.container_layout.addStretch()

    def _on_changed(self):
        self.btn_save.setEnabled(True)

    def save_changes(self):
        if not self.parser: return
        try:
            for (sec, key), le in self.widgets.items():
                new_val = le.text().strip()
                if new_val and (sec, key) in self.parser.sections:
                    _, line_idx = self.parser.sections[sec][key]
                    if new_val != self.parser.sections[sec][key][0]:
                        self.parser.raw_lines[line_idx] = f"{key}: {new_val}\n"

            with open(self._file_path, 'w', encoding='utf-8') as f:
                f.writelines(self.parser.raw_lines)

            self.parser.load()
            self.btn_save.setEnabled(False)
            self.status.setText(self.labels.get("ui", {}).get("status_saved", "💾 Сохранено"))
            QMessageBox.information(self, 
                self.labels.get("ui", {}).get("msg_save_title", "Готово"),
                self.labels.get("ui", {}).get("msg_save_text", "Изменения сохранены.")
            )
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e))

    def load_from_path(self, path: str):
        self.load_file(path)