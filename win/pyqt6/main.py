import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt

from app import BedMeshApp
from utils.logger import setup_logger
from utils.app_config import AppConfig

def main():
    # 1. Настройка окружения
    setup_logger()
    AppConfig().load()

    # 2. Инициализация приложения
    app = QApplication(sys.argv)
    app.setApplicationName("BedMesh Visualizer")
    app.setOrganizationName("rkfsociety")
    app.setStyle("Fusion")  # Кроссплатформенный стиль
    app.setAttribute(Qt.ApplicationAttribute.AA_EnableHighDpiScaling)

    # 3. Запуск главного окна
    window = BedMeshApp()
    window.show()

    # 4. Цикл событий
    sys.exit(app.exec())

if __name__ == "__main__":
    main()