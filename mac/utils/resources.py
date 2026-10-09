import os
import re
import sys
import tempfile
import urllib.request
from typing import Callable, Optional, Tuple

try:
    import requests  # type: ignore
except Exception:
    requests = None

# Версия берётся из main, бинарник — из соответствующего gkbridge GitHub Release.
GKBRIDGE_VERSION_URL = "https://raw.githubusercontent.com/rkfsociety/bedmesh/main/webpanel/gkbridge.version"
GKBRIDGE_RELEASE_URL = "https://github.com/rkfsociety/bedmesh/releases/download/v{}-gkbridge/gkbridge"
GKBRIDGE_LEGACY_URL = "https://raw.githubusercontent.com/rkfsociety/bedmesh/main/webpanel/gkbridge"
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
    в `_MEIPASS/resources/gkbridge` (см. CI), поэтому пути расходятся.
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

    def _download(url: str) -> None:
        if requests is not None:
            response = requests.get(url, stream=True, timeout=timeout)
            response.raise_for_status()
            with open(path, "wb") as f:
                for chunk in response.iter_content(chunk_size=256 * 1024):
                    if chunk:
                        f.write(chunk)
        else:
            request = urllib.request.Request(
                url,
                headers={"User-Agent": "rkfsociety-bedmesh-mac"},
                method="GET",
            )
            with urllib.request.urlopen(request, timeout=timeout) as response, open(path, "wb") as f:
                while True:
                    chunk = response.read(256 * 1024)
                    if not chunk:
                        break
                    f.write(chunk)
        if os.path.getsize(path) < _MIN_GKBRIDGE_BYTES:
            raise RuntimeError(f"gkbridge слишком маленький: {os.path.getsize(path)} байт")

    fd, path = tempfile.mkstemp(prefix="gkbridge_", suffix=".bin")
    os.close(fd)
    try:
        _p("Скачивание gkbridge с GitHub…")
        if requests is not None:
            version_response = requests.get(GKBRIDGE_VERSION_URL, timeout=timeout)
            version_response.raise_for_status()
            version = version_response.text.strip()
        else:
            version_request = urllib.request.Request(
                GKBRIDGE_VERSION_URL,
                headers={"User-Agent": "rkfsociety-bedmesh-mac"},
                method="GET",
            )
            with urllib.request.urlopen(version_request, timeout=timeout) as response:
                version = response.read(64).decode("ascii").strip()
        if not re.fullmatch(r"\d+(?:\.\d+){2}", version):
            raise RuntimeError(f"Некорректная версия gkbridge: {version!r}")
        download_url = GKBRIDGE_RELEASE_URL.format(version)
        try:
            _download(download_url)
        except Exception as release_error:
            _p(f"Релиз gkbridge пока недоступен ({release_error}); пробуем резервный бинарник…")
            try:
                _download(GKBRIDGE_LEGACY_URL)
            except Exception as fallback_error:
                raise RuntimeError(
                    "Не удалось скачать gkbridge из релиза или резервного источника: "
                    f"{fallback_error}"
                ) from release_error

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
