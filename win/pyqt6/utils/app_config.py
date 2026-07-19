import json
import os
from PyQt6.QtCore import QByteArray, QStandardPaths


def get_app_data_dir() -> str:
    # AppDataLocation already includes org/app name when set on QApplication.
    base_dir = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation)
    if not base_dir:
        base_dir = os.path.join(os.getenv("APPDATA") or os.getcwd(), "rkfsociety", "BedMesh Visualizer")
    os.makedirs(base_dir, exist_ok=True)
    return base_dir


def get_cache_dir() -> str:
    cache_dir = os.path.join(get_app_data_dir(), "cache")
    os.makedirs(cache_dir, exist_ok=True)
    return cache_dir


def default_download_local_path(remote_path: str) -> str:
    base_name = os.path.basename(remote_path) or "temp_download.cfg"
    return os.path.join(get_cache_dir(), f"download_{base_name}")


class AppConfig:
    def __init__(self):
        base_dir = get_app_data_dir()
        self.base_dir = base_dir
        self.file_path = os.path.join(base_dir, "settings.json")
        self.defaults = {
            "ssh_ip": "192.168.",
            "ssh_port": "2222",
            "ssh_user": "root",
            "ssh_pass": "rockchip",
            "ssh_path": "/userdata/app/gk/printer.cfg",
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
        # This option is UI-only and must not persist.
        self.settings.pop("show_advanced", None)
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