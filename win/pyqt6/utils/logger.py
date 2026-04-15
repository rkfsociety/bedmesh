import logging
import os
from logging.handlers import RotatingFileHandler
from PyQt6.QtCore import QStandardPaths

def _get_log_path() -> str:
    base_dir = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation)
    # If called before QApplication/QCoreApplication exists, Qt may return empty string.
    if not base_dir:
        base_dir = os.path.join(os.getenv("APPDATA") or os.getcwd(), "rkfsociety", "BedMesh Visualizer")
    os.makedirs(base_dir, exist_ok=True)
    return os.path.join(base_dir, "debug.log")

def get_log_file() -> str:
    return _get_log_path()

# Backward-compat for older code; avoid using this at import-time elsewhere.
LOG_FILE = get_log_file()
MAX_BYTES = 5 * 1024 * 1024

def setup_logger(level=logging.DEBUG, debug_mode: bool = True):
    root = logging.getLogger()
    root.setLevel(level)
    if root.hasHandlers(): root.handlers.clear()

    formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(name)s: %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
    
    console = logging.StreamHandler()
    console.setLevel(logging.INFO if not debug_mode else logging.DEBUG)
    console.setFormatter(formatter)
    root.addHandler(console)

    if debug_mode:
        log_file = get_log_file()
        file_handler = RotatingFileHandler(log_file, maxBytes=MAX_BYTES, backupCount=3, encoding='utf-8', delay=True)
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        root.addHandler(file_handler)

def get_logger(name):
    return logging.getLogger(name)

def open_log_file():
    import sys
    log_file = get_log_file()
    if os.path.exists(log_file):
        if sys.platform == 'win32': os.startfile(log_file)
        elif sys.platform == 'darwin': os.system(f'open "{log_file}"')
        else: os.system(f'xdg-open "{log_file}"')