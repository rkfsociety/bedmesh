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

    config = AppConfig()
    config.load()
    debug = config.get("debug_mode", "true") == "true"
    setup_logger(level=logging.DEBUG if debug else logging.INFO, debug_mode=debug)
    
    # Иконка (если есть)
    import os
    icon_path = os.path.join(os.getcwd(), "icon.ico")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    window = BedMeshApp()
    window.show()

    sys.exit(app.exec())

if __name__ == "__main__":
    main()