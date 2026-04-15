import sys
import logging
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QIcon

from app import BedMeshApp
from utils.logger import setup_logger
from utils.app_config import AppConfig

def main():
    app = QApplication(sys.argv)
    app.setApplicationName("BedMesh Visualizer")
    app.setOrganizationName("rkfsociety")
    app.setStyle("Fusion")

    # Для Windows: задаём AppUserModelID, чтобы иконка корректно отображалась в панели задач.
    # (Особенно важно для сборок PyInstaller onefile.)
    try:
        import ctypes  # noqa: WPS433
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("rkfsociety.bedmesh.visualizer")
    except Exception:
        pass

    config = AppConfig()
    config.load()
    debug = config.get("debug_mode", "true") == "true"
    setup_logger(level=logging.DEBUG if debug else logging.INFO, debug_mode=debug)
    
    # Иконка приложения/окна:
    # - если есть icon.ico рядом со скриптом (или в _MEIPASS) — берём его
    # - иначе в собранном .exe используем иконку самого exe (у ярлыка она обычно уже есть)
    import os
    icon_path = None
    try:
        base_dir = sys._MEIPASS if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS") else os.path.dirname(__file__)
        cand = os.path.join(base_dir, "icon.ico")
        if os.path.exists(cand):
            icon_path = cand
    except Exception:
        icon_path = None

    if icon_path:
        app.setWindowIcon(QIcon(icon_path))
    elif getattr(sys, "frozen", False):
        app.setWindowIcon(QIcon(sys.executable))

    window = BedMeshApp()
    # На всякий случай продублируем иконку на окно (в некоторых конфигурациях Qt это влияет на таскбар).
    try:
        window.setWindowIcon(app.windowIcon())
    except Exception:
        pass
    window.show()

    sys.exit(app.exec())

if __name__ == "__main__":
    main()