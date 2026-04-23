import logging
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication

from app import BedMeshApp
from utils.app_config import AppConfig
from utils.logger import setup_logger


def _detect_icon_path() -> str | None:
    try:
        if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
            base_dir = Path(sys._MEIPASS)
        else:
            base_dir = Path(__file__).resolve().parent

        candidates = [
            base_dir / "icon.icns",
            base_dir / "icon.png",
            base_dir.parent / "icon.icns",
            base_dir.parent / "icon.png",
        ]

        for candidate in candidates:
            if candidate.exists():
                return str(candidate)
    except Exception:
        return None
    return None


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("BedMesh Visualizer")
    app.setOrganizationName("rkfsociety")
    app.setStyle("Fusion")

    config = AppConfig()
    config.load()
    debug = config.get("debug_mode", "true") == "true"
    setup_logger(level=logging.DEBUG if debug else logging.INFO, debug_mode=debug)

    icon_path = _detect_icon_path()
    if icon_path:
        app.setWindowIcon(QIcon(icon_path))

    window = BedMeshApp()
    try:
        window.setWindowIcon(app.windowIcon())
    except Exception:
        pass
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
