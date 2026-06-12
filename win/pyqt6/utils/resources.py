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


def gkbridge_binary() -> str:
    """
    Путь к бинарнику веб-панели gkbridge.
    Исходник живёт в корневой папке репозитория `webpanel/`, в сборку он попадает
    в `_MEIPASS/resources/gkbridge` (см. .spec / CI), поэтому пути расходятся.
    """
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, "resources", "gkbridge")
    # dev: win/pyqt6/utils -> ../../.. = корень репозитория -> webpanel/gkbridge
    root = os.path.join(os.path.dirname(__file__), "..", "..", "..")
    return os.path.normpath(os.path.join(root, "webpanel", "gkbridge"))


def camera_dir() -> str:
    """
    Папка с файлами камеры (mjpg_streamer + плагины + libjpeg + cam-*.sh).
    Исходник — webpanel/camera/, в сборке — _MEIPASS/resources/camera/.
    """
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, "resources", "camera")
    root = os.path.join(os.path.dirname(__file__), "..", "..", "..")
    return os.path.normpath(os.path.join(root, "webpanel", "camera"))
