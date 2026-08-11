import os
import sys
import tempfile
import urllib.request
from typing import Callable, Optional, Tuple

try:
    import requests  # type: ignore
except Exception:
    requests = None

# Свежий бинарник панели на main (как Android SshInstaller).
GKBRIDGE_URL = "https://raw.githubusercontent.com/rkfsociety/bedmesh/main/webpanel/gkbridge"
_MIN_GKBRIDGE_BYTES = 1024 * 1024


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
    # dev: mac/utils -> ../.. = корень репозитория -> webpanel/gkbridge
    root = os.path.join(os.path.dirname(__file__), "..", "..")
    return os.path.normpath(os.path.join(root, "webpanel", "gkbridge"))


def download_gkbridge_from_github(
    progress_cb: Optional[Callable[[str], None]] = None,
    timeout: int = 120,
) -> str:
    """
    Скачивает актуальный gkbridge с GitHub во временный файл.
    Возвращает путь к файлу (вызывающий обязан удалить).
    Бросает исключение при ошибке / слишком маленьком файле.
    """
    def _p(msg: str):
        if progress_cb:
            try:
                progress_cb(msg)
            except Exception:
                pass

    fd, path = tempfile.mkstemp(prefix="gkbridge_", suffix=".bin")
    os.close(fd)
    try:
        _p("Скачивание gkbridge с GitHub…")
        if requests is not None:
            r = requests.get(GKBRIDGE_URL, stream=True, timeout=timeout)
            r.raise_for_status()
            with open(path, "wb") as f:
                for chunk in r.iter_content(chunk_size=256 * 1024):
                    if chunk:
                        f.write(chunk)
        else:
            req = urllib.request.Request(
                GKBRIDGE_URL,
                headers={"User-Agent": "rkfsociety-bedmesh-mac"},
                method="GET",
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp, open(path, "wb") as f:
                while True:
                    chunk = resp.read(256 * 1024)
                    if not chunk:
                        break
                    f.write(chunk)

        size = os.path.getsize(path)
        if size < _MIN_GKBRIDGE_BYTES:
            raise RuntimeError(f"gkbridge слишком маленький: {size} байт")
        _p(f"Скачано {size // (1024 * 1024)} МБ")
        return path
    except Exception:
        try:
            os.remove(path)
        except OSError:
            pass
        raise


def resolve_gkbridge_for_install(
    preferred_path: Optional[str] = None,
    progress_cb: Optional[Callable[[str], None]] = None,
) -> Tuple[str, bool]:
    """
    Путь к бинарнику для установки/обновления панели.
    Возвращает (path, is_temp): сначала GitHub, иначе встроенный/локальный.
    """
    if preferred_path:
        return preferred_path, False
    try:
        return download_gkbridge_from_github(progress_cb=progress_cb), True
    except Exception as e:
        if progress_cb:
            try:
                progress_cb(f"GitHub недоступен ({e}), используем встроенный бинарник…")
            except Exception:
                pass
        local = gkbridge_binary()
        if not os.path.exists(local):
            raise FileNotFoundError(f"gkbridge не найден локально: {local}") from e
        return local, False


def camera_dir() -> str:
    """
    Папка с файлами камеры (mjpg_streamer + плагины + libjpeg + cam-*.sh).
    Исходник — webpanel/camera/, в сборке — _MEIPASS/resources/camera/.
    """
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, "resources", "camera")
    root = os.path.join(os.path.dirname(__file__), "..", "..")
    return os.path.normpath(os.path.join(root, "webpanel", "camera"))
