import json
import os
import re
import sys
import threading
import webbrowser
from typing import Callable, Optional, Tuple

import urllib.error
import urllib.request

try:
    import requests  # type: ignore
except Exception:  # pragma: no cover
    requests = None

from PyQt6.QtWidgets import QMessageBox


REPO = "rkfsociety/bedmesh"


def _http_get_json(url: str, timeout: int = 5) -> Optional[dict]:
    try:
        if requests is not None:
            response = requests.get(url, timeout=timeout)
            if response.status_code != 200:
                return None
            return response.json()

        request = urllib.request.Request(
            url,
            headers={
                "User-Agent": "rkfsociety-bedmesh-updater",
                "Accept": "application/vnd.github+json",
            },
            method="GET",
        )
        with urllib.request.urlopen(request, timeout=timeout) as response:
            if getattr(response, "status", 200) != 200:
                return None
            raw = response.read()
        return json.loads(raw.decode("utf-8", errors="replace"))
    except Exception:
        return None


def _parse_version_numbers(version: str) -> Tuple[int, ...]:
    version = (version or "").strip().lower()
    version = version.replace("v", "")
    version = version.split("-", 1)[0]
    parts = [part for part in re.split(r"[^\d]+", version) if part]
    return tuple(int(part) for part in parts) if parts else (0,)


def is_new_version(current: str, remote: str) -> bool:
    try:
        return _parse_version_numbers(remote) > _parse_version_numbers(current)
    except Exception:
        return (remote or "") > (current or "")


def _has_macos_asset(release_data: dict) -> bool:
    assets = release_data.get("assets") or []
    return any((asset.get("name") or "").lower().endswith(".dmg") for asset in assets)


def check_for_updates_detailed(
    current_version: str,
    result_callback: Callable[[str, Optional[str], Optional[dict]], None],
) -> None:
    def task():
        try:
            data = _http_get_json(f"https://api.github.com/repos/{REPO}/releases/latest", timeout=5)
            if not data:
                result_callback("error", None, None)
                return

            latest_tag = (data.get("tag_name") or "").strip()
            if not latest_tag:
                result_callback("error", None, None)
                return

            if _has_macos_asset(data) and is_new_version(current_version, latest_tag):
                result_callback("update", latest_tag, data)
            else:
                result_callback("none", latest_tag, data)
        except Exception:
            result_callback("error", None, None)

    threading.Thread(target=task, daemon=True).start()


def install_update(release_data: dict, parent=None) -> None:
    assets = release_data.get("assets") or []
    if not any((asset.get("name") or "").lower().endswith(".dmg") for asset in assets):
        QMessageBox.information(
            parent,
            "Обновление",
            "Для этого релиза не найден macOS-установщик. Открою страницу Releases.",
        )
    webbrowser.open(f"https://github.com/{REPO}/releases/latest")
