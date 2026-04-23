import json
import os
import sys


class StringManager:
    def __init__(self, lang: str = "ru"):
        self._data = {}
        self._load(lang)

    def _load(self, lang: str):
        if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
            base_dir = sys._MEIPASS
            path = os.path.join(base_dir, "ui", "locale", f"{lang}.json")
        else:
            path = os.path.join(os.path.dirname(__file__), "..", "ui", "locale", f"{lang}.json")
        try:
            with open(path, "r", encoding="utf-8") as file_obj:
                self._data = json.load(file_obj)
        except Exception:
            self._data = {}

    def get(self, key: str, **kwargs) -> str:
        keys = key.split(".")
        value = self._data
        for key_part in keys:
            if isinstance(value, dict) and key_part in value:
                value = value[key_part]
            else:
                return key
        return value.format(**kwargs) if kwargs and isinstance(value, str) else value


S = StringManager()
