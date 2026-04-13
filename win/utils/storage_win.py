import json
import os

SETTINGS_FILE = "settings_win.json"

# Дефолтные настройки, чтобы программа всегда знала, что подставить
DEFAULT_SETTINGS = {
    "z_sys": "Винты (углы)",
    "pitch": "0.7",
    "gx": 5,
    "gy": 5,
    "last_ip": "192.168.1.1",
    "show_mutable": False
}

def load_settings():
    """Загружает настройки и объединяет их с дефолтными"""
    settings = DEFAULT_SETTINGS.copy()
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                loaded = json.load(f)
                settings.update(loaded) # Обновляем дефолты тем, что реально сохранено
        except Exception as e:
            print(f"Ошибка загрузки настроек: {e}")
    return settings

def save_settings(data):
    """Сохраняет данные в файл"""
    try:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"Ошибка сохранения настроек: {e}")