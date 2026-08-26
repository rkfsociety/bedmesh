import os
import sys
import logging


_QT_DLL_DIRECTORY_HANDLES = []


def _prepare_frozen_qt_dll_path() -> None:
    """Make PyQt6's nested Qt DLL directory visible before importing QtWidgets."""
    if not getattr(sys, "frozen", False) or not hasattr(sys, "_MEIPASS"):
        return
    qt_bin = os.path.join(sys._MEIPASS, "PyQt6", "Qt6", "bin")
    if not os.path.isdir(qt_bin):
        return
    os.environ["PATH"] = qt_bin + os.pathsep + os.environ.get("PATH", "")
    global _QT_DLL_DIRECTORY_HANDLES
    try:
        # Keep the handle alive for the lifetime of the process.  Dropping it
        # immediately removes the directory from the Windows DLL search path.
        _QT_DLL_DIRECTORY_HANDLES.append(os.add_dll_directory(sys._MEIPASS))
        _QT_DLL_DIRECTORY_HANDLES.append(os.add_dll_directory(qt_bin))
    except (AttributeError, OSError):
        # PATH is sufficient on older Windows/Python combinations.
        pass


_prepare_frozen_qt_dll_path()

from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QIcon

from app import BedMeshApp
from utils.logger import setup_logger
from utils.app_config import AppConfig
from ui.theme import apply_app_theme

def main():
    app = QApplication(sys.argv)
    app.setApplicationName("BedMesh Visualizer")
    app.setOrganizationName("rkfsociety")
    app.setStyle("Fusion")
    apply_app_theme(app)

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
