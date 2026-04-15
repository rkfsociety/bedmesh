import json
import os
from PyQt6.QtCore import QByteArray

class AppConfig:
    def __init__(self):
        self.file_path = os.path.join(os.getcwd(), "settings.json")
        self.defaults = {
            "ssh_ip": "192.168.",
            "ssh_port": "2222",
            "ssh_user": "root",
            "ssh_pass": "rockchip",
            "ssh_path": "/userdata/app/gk/printer.cfg",
            "show_advanced": "false",
            "debug_mode": "true",
            "window_geometry": ""
        }
        self.settings = self.defaults.copy()

    def _migrate(self):
        # Если раньше использовали printer_mutable.cfg по умолчанию — переедем на printer.cfg
        old = "/userdata/app/gk/printer_mutable.cfg"
        new = "/userdata/app/gk/printer.cfg"
        if self.settings.get("ssh_path") == old:
            self.settings["ssh_path"] = new

    def load(self):
        if os.path.exists(self.file_path):
            try:
                with open(self.file_path, 'r', encoding='utf-8') as f:
                    self.settings.update(json.load(f))
            except Exception: pass
        self._migrate()
        return self.settings

    def save(self):
        try:
            with open(self.file_path, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, indent=2, ensure_ascii=False)
        except Exception as e: print(f"Config save error: {e}")

    def get(self, key, default=None):
        return self.settings.get(key, default)

    def set(self, key, value):
        self.settings[key] = value
        self.save()

    def get_window_geometry(self):
        hex_data = self.settings.get("window_geometry", "")
        return QByteArray.fromHex(hex_data.encode()) if hex_data else None

    def save_window_geometry(self, geometry: QByteArray):
        if geometry:
            self.set("window_geometry", geometry.toHex().data().decode())