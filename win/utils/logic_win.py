import os
import sys

VERSION = "0.139-win" 

def resource_path(relative_path):
    """ Получает абсолютный путь к ресурсам, работает для dev и для PyInstaller """
    try:
        # PyInstaller создает временную папку _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)