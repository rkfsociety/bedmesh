import logging
import os
import sys
from datetime import datetime

# Настройка путей
if getattr(sys, 'frozen', False):
    # Если запущено из .exe, лог кладем рядом с файлом
    log_dir = os.path.dirname(sys.executable)
else:
    # Если запущено из Python, лог кладем в корень проекта
    log_dir = os.path.dirname(os.path.abspath(__file__))
    log_dir = os.path.dirname(log_dir) # Поднимаемся из папки utils в корень

LOG_FILE = os.path.join(log_dir, "app.log")

# Настройка формата логов
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE, encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)

def info(message):
    logging.info(message)

def error(message):
    logging.error(message)

def warning(message):
    logging.warning(message)

def debug(message):
    logging.debug(message)