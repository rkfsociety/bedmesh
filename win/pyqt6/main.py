import sys
from PyQt6.QtWidgets import QApplication

from app import BedMeshApp
from utils.logger import setup_logger
from utils.app_config import AppConfig

def main():
    setup_logger()
    AppConfig().load()

    app = QApplication(sys.argv)
    app.setApplicationName("BedMesh Visualizer")
    app.setOrganizationName("rkfsociety")
    app.setStyle("Fusion")

    window = BedMeshApp()
    window.show()

    sys.exit(app.exec())

if __name__ == "__main__":
    main()