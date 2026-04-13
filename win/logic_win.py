import os, sys

# Актуальная версия с новой логикой парсинга и расширенным анализом
VERSION = "0.137-win" 

def resource_path(relative_path):
    """
    Определяет путь к ресурсам (иконки и т.д.) для PyInstaller.
    """
    try:
        # Путь временной папки PyInstaller
        base_path = sys._MEIPASS
    except Exception:
        # Обычный путь при запуске .py
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)