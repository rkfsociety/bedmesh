import os
import sys

# Актуальная версия приложения
VERSION = "0.150-win" 

def resource_path(relative_path):
    """ 
    Получает абсолютный путь к ресурсам. 
    Необходим для того, чтобы PyInstaller видел иконку внутри .exe
    """
    try:
        # Путь временной папки PyInstaller
        base_path = sys._MEIPASS
    except Exception:
        # Обычный путь при запуске через VS Code
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)