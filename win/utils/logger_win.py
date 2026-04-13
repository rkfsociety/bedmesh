import logging
import os
import sys

# Настройка путей
log_file = "debug.log"

# Создаем форматтер
formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')

# Настройка логгера
logger = logging.getLogger("BedMeshDebug")
logger.setLevel(logging.DEBUG)

# Обработчик для записи в файл
file_handler = logging.FileHandler(log_file, encoding='utf-8')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

# Обработчик для вывода в консоль
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

def info(msg):
    logger.info(msg)

def error(msg):
    logger.error(msg)

def warning(msg):
    logger.warning(msg)

def debug(msg):
    logger.debug(msg)