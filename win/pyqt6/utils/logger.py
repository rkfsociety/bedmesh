import logging
import os
from logging.handlers import RotatingFileHandler

LOG_FILE = "debug.log"
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
        file_handler = RotatingFileHandler(LOG_FILE, maxBytes=MAX_BYTES, backupCount=3, encoding='utf-8', delay=True)
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        root.addHandler(file_handler)

def get_logger(name):
    return logging.getLogger(name)

def open_log_file():
    import sys
    if os.path.exists(LOG_FILE):
        if sys.platform == 'win32': os.startfile(LOG_FILE)
        elif sys.platform == 'darwin': os.system(f'open "{LOG_FILE}"')
        else: os.system(f'xdg-open "{LOG_FILE}"')