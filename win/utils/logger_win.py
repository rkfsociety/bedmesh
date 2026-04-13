import logging
import os
import sys

# Определяем путь к папке с логами (рядом с .exe или скриптом)
if getattr(sys, 'frozen', False):
    base_path = os.path.dirname(sys.executable)
else:
    base_path = os.path.dirname(os.path.abspath(__file__))
    base_path = os.path.dirname(base_path) # Выход из utils в корень

LOG_FILE = os.path.join(base_path, "app.log")

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE, encoding='utf-8'),
        logging.StreamHandler(sys.stdout) # Дублируем в консоль VS Code
    ]
)

def info(msg): logging.info(msg)
def error(msg): logging.error(msg)
def warning(msg): logging.warning(msg)