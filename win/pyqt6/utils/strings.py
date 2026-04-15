import json
import os

class StringManager:
    def __init__(self, lang: str = "ru"):
        self._data = {}
        self._load(lang)

    def _load(self, lang: str):
        path = os.path.join(os.path.dirname(__file__), "..", "ui", "locale", f"{lang}.json")
        try:
            with open(path, "r", encoding="utf-8") as f:
                self._data = json.load(f)
        except Exception:
            self._data = {}

    def get(self, key: str, **kwargs) -> str:
        keys = key.split(".")
        val = self._data
        for k in keys:
            if isinstance(val, dict) and k in val:
                val = val[k]
            else:
                return key  # Фолбэк: если ключа нет, вернёт сам ключ
        return val.format(**kwargs) if kwargs and isinstance(val, str) else val

# Глобальный экземпляр (загружается один раз при первом импорте)
S = StringManager()