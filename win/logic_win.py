import os, sys

VERSION = "0.107-win" 

def resource_path(relative_path):
    """Путь для упаковки ресурсов в EXE"""
    try: base_path = sys._MEIPASS
    except Exception: base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)