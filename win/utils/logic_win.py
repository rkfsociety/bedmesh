import os
import sys

# Актуальная версия приложения
VERSION = "0.151-win" 

def resource_path(relative_path):
    """ Получает абсолютный путь к ресурсам для PyInstaller """
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

def check_updates():
    """ 
    Заглушка для совместимости. 
    Основная логика теперь в updater_win.py 
    """
    return True