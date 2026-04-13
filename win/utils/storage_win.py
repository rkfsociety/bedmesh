import json
import os
import sys
from utils import logger_win

# Имя файла настроек
SETTINGS_FILE = "settings_win.json"

def get_settings_path():
    """Определяет путь к конфигу рядом с .exe или основным скриптом"""
    if getattr(sys, 'frozen', False):
        # Если запущено как .exe
        base_path = os.path.dirname(sys.executable)
    else:
        # Если запущено как скрипт .py
        base_path = os.path.abspath(".")
    
    return os.path.join(base_path, SETTINGS_FILE)

def load_settings():
    """Загрузка настроек из JSON"""
    path = get_settings_path()
    
    # Дефолтные значения, если файла нет
    defaults = {
        "host": "192.168.1.1",
        "port": "2222",
        "user": "root",
        "password": "rockchip",
        "path": "/userdata/app/gk/printer_mutable.cfg",
        "path_cfg": "/userdata/app/gk/printer.cfg",
        "bed_x": "250",
        "bed_y": "250",
        "grid_x": "5",
        "grid_y": "5",
        "show_mutable": False,
        "z_sys": "Валы (2 перед, 1 зад)",
        "pitch": "0.7"
    }

    if not os.path.exists(path):
        logger_win.info(f"Файл настроек не найден. Используются дефолты.")
        return defaults

    try:
        with open(path, "r", encoding="utf-8") as f:
            loaded = json.load(f)
            # Склеиваем дефолты с загруженными данными (на случай отсутствия ключей)
            defaults.update(loaded)
            logger_win.info(f"Настройки успешно загружены из: {path}")
            return defaults
    except Exception as e:
        logger_win.error(f"Ошибка при загрузке настроек: {e}")
        return defaults

def save_settings(settings):
    """Сохранение настроек в JSON"""
    path = get_settings_path()
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=4, ensure_ascii=False)
        logger_win.info(f"Настройки сохранены в: {path}")
    except Exception as e:
        logger_win.error(f"Ошибка при сохранении настроек: {e}")