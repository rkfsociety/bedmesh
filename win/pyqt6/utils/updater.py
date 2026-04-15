import os
import re
import sys
import subprocess
import threading
import webbrowser
from typing import Callable, Optional, Tuple

import requests
from PyQt6.QtWidgets import QMessageBox


REPO = "rkfsociety/bedmesh"


def _parse_version_numbers(v: str) -> Tuple[int, ...]:
    """
    Extracts numeric version tuple from strings like:
    - "0.151-win"
    - "v0.151-win"
    - "0.151"
    """
    v = (v or "").strip().lower()
    v = v.replace("v", "")
    v = v.split("-", 1)[0]
    parts = [p for p in re.split(r"[^\d]+", v) if p]
    return tuple(int(p) for p in parts) if parts else (0,)


def is_new_version(current: str, remote: str) -> bool:
    try:
        return _parse_version_numbers(remote) > _parse_version_numbers(current)
    except Exception:
        return (remote or "") > (current or "")


def _is_frozen_exe() -> bool:
    return bool(getattr(sys, "frozen", False)) and (sys.executable or "").lower().endswith(".exe")


def check_for_updates(current_version: str, update_callback: Callable[[str, dict], None]) -> None:
    """
    Background check against GitHub Releases latest.
    Calls update_callback(latest_tag, release_json) if a newer Windows release exists and has .exe asset.
    """

    def task():
        try:
            r = requests.get(f"https://api.github.com/repos/{REPO}/releases/latest", timeout=5)
            if r.status_code != 200:
                return
            data = r.json()
            latest_tag = (data.get("tag_name") or "").strip()  # e.g. "v0.151-win"
            if not latest_tag:
                return

            tag_l = latest_tag.lower()
            if "-mac" in tag_l and "-win" not in tag_l:
                return

            if not is_new_version(current_version, latest_tag):
                return

            assets = data.get("assets") or []
            if not any((a.get("name") or "").lower().endswith(".exe") for a in assets):
                return

            update_callback(latest_tag, data)
        except Exception:
            return

    threading.Thread(target=task, daemon=True).start()


def check_for_updates_detailed(
    current_version: str,
    result_callback: Callable[[str, Optional[str], Optional[dict]], None],
) -> None:
    """
    Background check against GitHub Releases latest.
    Calls result_callback(status, latest_tag, release_json)
    status: "update" | "none" | "error"
    """

    def task():
        try:
            r = requests.get(f"https://api.github.com/repos/{REPO}/releases/latest", timeout=5)
            if r.status_code != 200:
                result_callback("error", None, None)
                return
            data = r.json()
            latest_tag = (data.get("tag_name") or "").strip()
            if not latest_tag:
                result_callback("error", None, None)
                return

            tag_l = latest_tag.lower()
            if "-mac" in tag_l and "-win" not in tag_l:
                result_callback("none", latest_tag, data)
                return

            assets = data.get("assets") or []
            has_exe = any((a.get("name") or "").lower().endswith(".exe") for a in assets)
            if has_exe and is_new_version(current_version, latest_tag):
                result_callback("update", latest_tag, data)
            else:
                result_callback("none", latest_tag, data)
        except Exception:
            result_callback("error", None, None)

    threading.Thread(target=task, daemon=True).start()


def install_update(release_data: dict, parent=None) -> None:
    """
    For onefile exe builds:
    - downloads latest .exe to app folder as temp file
    - writes a .bat that waits, replaces current exe, restarts app, then deletes itself
    For non-frozen runs (dev), opens the Releases page.
    """
    try:
        if not _is_frozen_exe():
            webbrowser.open(f"https://github.com/{REPO}/releases/latest")
            return

        assets = release_data.get("assets") or []
        url = None
        for a in assets:
            name = (a.get("name") or "").lower()
            if name.endswith(".exe"):
                url = a.get("browser_download_url")
                break
        if not url:
            QMessageBox.warning(parent, "Update", "Не найден .exe файл в релизе.")
            return

        current_exe = os.path.abspath(sys.executable)
        base_dir = os.path.dirname(current_exe)
        new_exe_name = "BedMesh_Update_Temp.exe"
        new_exe_path = os.path.join(base_dir, new_exe_name)

        r = requests.get(url, stream=True, timeout=30)
        r.raise_for_status()
        with open(new_exe_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=1024 * 256):
                if chunk:
                    f.write(chunk)

        current_exe_name = os.path.basename(current_exe)
        bat_path = os.path.join(base_dir, "updater_pyqt6.bat")

        with open(bat_path, "w", encoding="cp866") as f:
            f.write("@echo off\n")
            f.write("title Updating BedMesh Visualizer...\n")
            f.write(f'echo Closing process "{current_exe_name}"...\n')
            f.write(f'taskkill /f /im "{current_exe_name}" >nul 2>&1\n')
            f.write("timeout /t 2 /nobreak > nul\n")
            f.write(":loop\n")
            f.write(f'del /f /q "{current_exe}" >nul 2>&1\n')
            f.write(f'if exist "{current_exe}" (timeout /t 1 /nobreak > nul & goto loop)\n')
            f.write("echo Installing new version...\n")
            f.write(f'move /y "{new_exe_name}" "{current_exe}" >nul\n')
            f.write("echo Starting application...\n")
            f.write(f'start "" "{current_exe}"\n')
            f.write('del "%~f0"\n')

        QMessageBox.information(
            parent,
            "Update",
            "Загрузка завершена. Программа закроется на несколько секунд для установки обновления.",
        )
        subprocess.Popen(f'start "" "{bat_path}"', shell=True)
        os._exit(0)
    except Exception as e:
        QMessageBox.critical(parent, "Update Error", f"Не удалось установить обновление:\n{str(e)}")

