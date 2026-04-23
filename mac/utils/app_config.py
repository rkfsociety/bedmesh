import json
import os

from PyQt6.QtCore import QByteArray, QStandardPaths


class AppConfig:
    def __init__(self):
        base_dir = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation)
        if not base_dir:
            home = os.path.expanduser("~")
            base_dir = os.path.join(home, "Library", "Application Support", "rkfsociety", "BedMesh Visualizer")
        os.makedirs(base_dir, exist_ok=True)
        self.base_dir = base_dir
        self.file_path = os.path.join(base_dir, "settings.json")
        self.defaults = {
            "ssh_ip": "192.168.",
            "ssh_port": "2222",
            "ssh_user": "root",
            "ssh_pass": "rockchip",
            "ssh_path": "/userdata/app/gk/printer.cfg",
            "debug_mode": "true",
            "window_geometry": "",
        }
        self.settings = self.defaults.copy()

    def _migrate(self):
        old_path = "/userdata/app/gk/printer_mutable.cfg"
        new_path = "/userdata/app/gk/printer.cfg"
        if self.settings.get("ssh_path") == old_path:
            self.settings["ssh_path"] = new_path

    def load(self):
        if os.path.exists(self.file_path):
            try:
                with open(self.file_path, "r", encoding="utf-8") as file_obj:
                    self.settings.update(json.load(file_obj))
            except Exception:
                pass
        self.settings.pop("show_advanced", None)
        self._migrate()
        return self.settings

    def save(self):
        try:
            with open(self.file_path, "w", encoding="utf-8") as file_obj:
                json.dump(self.settings, file_obj, indent=2, ensure_ascii=False)
        except Exception as error:
            print(f"Config save error: {error}")

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
