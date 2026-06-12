import os
import sys


def resource_path(rel: str) -> str:
    """
    Возвращает абсолютный путь к ресурсу, корректный и при запуске из исходников,
    и в onefile-сборке PyInstaller (ресурсы распакованы в sys._MEIPASS).
    `rel` — путь относительно корня проекта (например, "resources/gkbridge").
    """
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        base_dir = sys._MEIPASS
    else:
        # utils/ -> корень проекта на уровень выше
        base_dir = os.path.join(os.path.dirname(__file__), "..")
    return os.path.normpath(os.path.join(base_dir, rel))
