import os
import re
import sys
import subprocess
import threading
import webbrowser
from typing import Callable, Optional, Tuple

import json
import urllib.request
import urllib.error

try:
    import requests  # type: ignore
except Exception:  # pragma: no cover
    requests = None
from PyQt6.QtWidgets import (QMessageBox, QProgressDialog, QDialog, QVBoxLayout,
                             QHBoxLayout, QLabel, QTextBrowser, QPushButton)
from PyQt6.QtCore import QTimer, Qt


REPO = "rkfsociety/bedmesh"


def _http_get_json(url: str, timeout: int = 5):
    """
    Lightweight HTTP JSON GET with stdlib fallback.
    Keep the app runnable even if 'requests' isn't installed.
    Returns parsed JSON (dict or list) or None.
    """
    try:
        if requests is not None:
            r = requests.get(url, timeout=timeout)
            if r.status_code != 200:
                return None
            return r.json()

        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "rkfsociety-bedmesh-updater",
                "Accept": "application/vnd.github+json",
            },
            method="GET",
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            if getattr(resp, "status", 200) != 200:
                return None
            raw = resp.read()
        return json.loads(raw.decode("utf-8", errors="replace"))
    except Exception:
        return None


def _latest_release_for_platform(*, tag_suffix: str, asset_ext: str) -> Optional[dict]:
    """
    GitHub /releases/latest is global (last published of any platform).
    Pick the newest non-draft release whose tag contains -<suffix> and has the asset.
    """
    payload = _http_get_json(f"https://api.github.com/repos/{REPO}/releases?per_page=40", timeout=8)
    if not isinstance(payload, list) or not payload:
        return None

    needle = f"-{tag_suffix.lower()}"
    ext = asset_ext.lower()
    candidates: list[dict] = []
    for rel in payload:
        if not isinstance(rel, dict):
            continue
        if rel.get("draft") or rel.get("prerelease"):
            continue
        tag = (rel.get("tag_name") or "").strip().lower()
        if needle not in tag:
            continue
        assets = rel.get("assets") or []
        if not any((a.get("name") or "").lower().endswith(ext) for a in assets if isinstance(a, dict)):
            continue
        candidates.append(rel)

    if not candidates:
        return None
    return max(candidates, key=lambda r: _parse_version_numbers(r.get("tag_name") or ""))


def _http_download_stream(
    url: str,
    target_path: str,
    *,
    chunk_size: int = 1024 * 256,
    timeout: int = 30,
    on_chunk=None,
) -> None:
    """
    Streaming download with optional progress callback: on_chunk(bytes_written, total_bytes_or_0)
    """
    if requests is not None:
        r = requests.get(url, stream=True, timeout=timeout)
        r.raise_for_status()
        total = int(r.headers.get("Content-Length") or 0)
        written = 0
        with open(target_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=chunk_size):
                if not chunk:
                    continue
                f.write(chunk)
                written += len(chunk)
                if on_chunk:
                    on_chunk(written, total)
        return

    req = urllib.request.Request(url, headers={"User-Agent": "rkfsociety-bedmesh-updater"}, method="GET")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        total = int(resp.headers.get("Content-Length") or 0)
        written = 0
        with open(target_path, "wb") as f:
            while True:
                chunk = resp.read(chunk_size)
                if not chunk:
                    break
                f.write(chunk)
                written += len(chunk)
                if on_chunk:
                    on_chunk(written, total)


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
    Background check for the newest Windows release (tag *-win with .exe).
    Calls update_callback(latest_tag, release_json) if newer than current_version.
    """

    def task():
        try:
            data = _latest_release_for_platform(tag_suffix="win", asset_ext=".exe")
            if not data:
                return
            latest_tag = (data.get("tag_name") or "").strip()
            if not latest_tag:
                return
            if not is_new_version(current_version, latest_tag):
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
    Background check for the newest Windows release (not GitHub global /latest).
    Calls result_callback(status, latest_tag, release_json)
    status: "update" | "none" | "error"
    """

    def task():
        try:
            data = _latest_release_for_platform(tag_suffix="win", asset_ext=".exe")
            if not data:
                result_callback("error", None, None)
                return
            latest_tag = (data.get("tag_name") or "").strip()
            if not latest_tag:
                result_callback("error", None, None)
                return

            if is_new_version(current_version, latest_tag):
                result_callback("update", latest_tag, data)
            else:
                result_callback("none", latest_tag, data)
        except Exception:
            result_callback("error", None, None)

    threading.Thread(target=task, daemon=True).start()


def _show_changelog_dialog(release_data: dict, parent=None) -> bool:
    """
    Показывает окно с описанием обновления и кнопкой «Скачать».
    Возвращает True, если пользователь решил скачивать.
    """
    tag = (release_data.get("tag_name") or "").strip()
    name = (release_data.get("name") or tag or "Обновление").strip()
    body = (release_data.get("body") or "").strip() or "Описание не указано."

    dlg = QDialog(parent)
    dlg.setWindowTitle("Доступно обновление")
    dlg.setModal(True)
    dlg.resize(640, 520)

    layout = QVBoxLayout(dlg)
    layout.setContentsMargins(16, 16, 16, 16)
    layout.setSpacing(12)

    title = QLabel(f"Доступна новая версия: <b>{name}</b>")
    title.setStyleSheet("font-size: 15px;")
    title.setTextFormat(Qt.TextFormat.RichText)
    layout.addWidget(title)

    notes = QTextBrowser()
    notes.setOpenExternalLinks(True)
    try:
        notes.setMarkdown(body)
    except Exception:
        notes.setPlainText(body)
    layout.addWidget(notes, 1)

    btn_row = QHBoxLayout()
    btn_row.addStretch()
    btn_later = QPushButton("Позже")
    btn_download = QPushButton("⬇  Скачать и установить")
    btn_download.setDefault(True)
    btn_download.setStyleSheet("background-color: #2d5a2d; color: white; padding: 6px 16px;")
    btn_row.addWidget(btn_later)
    btn_row.addWidget(btn_download)
    layout.addLayout(btn_row)

    btn_later.clicked.connect(dlg.reject)
    btn_download.clicked.connect(dlg.accept)

    return dlg.exec() == QDialog.DialogCode.Accepted


def install_update(release_data: dict, parent=None) -> None:
    """
    For onefile exe builds:
    - shows a changelog dialog; if confirmed, downloads latest .exe to app folder
    - writes a .bat that waits, replaces current exe, restarts app, then deletes itself
    For non-frozen runs (dev), opens the Releases page.
    """
    try:
        # Сначала показываем описание обновления и ждём подтверждения.
        if not _show_changelog_dialog(release_data, parent):
            return

        if not _is_frozen_exe():
            webbrowser.open(f"https://github.com/{REPO}/releases/latest")
            return

        assets = release_data.get("assets") or []
        url = None
        expected_size = None
        for a in assets:
            name = (a.get("name") or "").lower()
            if name.endswith(".exe"):
                url = a.get("browser_download_url")
                expected_size = a.get("size")
                break
        if not url:
            QMessageBox.warning(parent, "Обновление", "Не найден .exe файл в релизе.")
            return

        current_exe = os.path.abspath(sys.executable)
        base_dir = os.path.dirname(current_exe)
        new_exe_name = "BedMesh_Update_Temp.exe"
        new_exe_path = os.path.join(base_dir, new_exe_name)

        # --- Скачивание в фоне + прогресс, чтобы UI не зависал ---
        state = {"done": False, "error": None, "bytes": 0, "total": 0}

        def download_task():
            try:
                # если заголовок Content-Length не придёт, используем размер ассета из GitHub API
                if isinstance(expected_size, int) and expected_size > 0:
                    state["total"] = expected_size
                def on_chunk(written: int, total: int):
                    state["bytes"] = written
                    if total > 0:
                        state["total"] = total

                _http_download_stream(url, new_exe_path, chunk_size=1024 * 256, timeout=30, on_chunk=on_chunk)
                state["done"] = True
            except Exception as e:
                state["error"] = str(e)
                state["done"] = True

        dlg = QProgressDialog("Скачивание обновления…", None, 0, 100, parent)
        dlg.setWindowTitle("Обновление")
        dlg.setWindowModality(Qt.WindowModality.ApplicationModal)
        dlg.setAutoClose(False)
        dlg.setAutoReset(False)
        dlg.setCancelButton(None)
        dlg.setMinimumDuration(0)
        dlg.show()

        t = threading.Thread(target=download_task, daemon=True)
        t.start()

        # Важно: таймер должен жить, иначе он может быть GC и окно зависнет “навсегда”.
        timer = QTimer(dlg)

        def on_tick():
            if state["done"]:
                timer.stop()
                dlg.close()
                if state["error"]:
                    QMessageBox.critical(parent, "Ошибка обновления", f"Не удалось скачать обновление:\n{state['error']}")
                    return
                # Проверка целостности по размеру ассета (если GitHub отдал размер).
                if isinstance(expected_size, int) and expected_size > 0 and state["bytes"] != expected_size:
                    QMessageBox.critical(
                        parent,
                        "Ошибка обновления",
                        "Скачанный файл повреждён (не совпал размер).\n"
                        f"Ожидалось: {expected_size} байт\n"
                        f"Скачано: {state['bytes']} байт\n"
                        "Попробуйте ещё раз.",
                    )
                    try:
                        os.remove(new_exe_path)
                    except Exception:
                        pass
                    return
                _run_replace_script(current_exe, new_exe_name, base_dir, parent)
                return

            total = state["total"]
            got = state["bytes"]
            if total > 0:
                pct = min(100, int(got * 100 / total))
                dlg.setMaximum(100)
                dlg.setValue(pct)
                mb = 1024 * 1024
                dlg.setLabelText(f"Скачивание обновления… {pct}%  ({got/mb:.1f}/{total/mb:.1f} МБ)")
            else:
                # Если сервер не дал Content-Length — пусть будет “пульсирующий” прогресс.
                dlg.setMaximum(0)
                dlg.setLabelText("Скачивание обновления…")

        timer.timeout.connect(on_tick)
        timer.start(100)
        return
    except Exception as e:
        QMessageBox.critical(parent, "Ошибка обновления", f"Не удалось установить обновление:\n{str(e)}")


def _build_replace_bat_content(*, current_exe: str, new_exe_path: str, current_exe_name: str) -> str:
    """Текст updater_pyqt6.bat: замена exe + чистка legacy _MEI* рядом с exe."""
    base_dir = os.path.dirname(current_exe)
    lines = [
        "@echo off",
        "setlocal",
        "set tries=0",
        f'taskkill /f /im "{current_exe_name}" >nul 2>&1',
        "timeout /t 4 /nobreak > nul",
        ":loop",
        f'del /f /q "{current_exe}" >nul 2>&1',
        f'if exist "{current_exe}" (timeout /t 1 /nobreak > nul & goto loop)',
        # Полный путь: cwd у cmd часто не папка с exe (Desktop / System32).
        f'move /y "{new_exe_path}" "{current_exe}" >nul',
        f'if exist "{new_exe_path}" del /f /q "{new_exe_path}" >nul 2>&1',
        r"rem Legacy _MEI next to exe from old builds. New runtime: %LOCALAPPDATA%\rkfsociety\BedMesh Visualizer\runtime",
        f'for /d %%D in ("{base_dir}\\_MEI*") do rd /s /q "%%~fD" >nul 2>&1',
        "timeout /t 3 /nobreak > nul",
        ":startloop",
        'set "RUNNING="',
        f'start "" "{current_exe}" >nul 2>&1',
        "timeout /t 2 /nobreak > nul",
        (
            f'for /f "tokens=*" %%p in (\'tasklist /fi "imagename eq {current_exe_name}" '
            f'^| find /i "{current_exe_name}" \') do set RUNNING=1'
        ),
        "if defined RUNNING goto started",
        "set /a tries+=1",
        "if %tries% GEQ 6 goto started",
        "goto startloop",
        ":started",
        "endlocal",
        'del "%~f0"',
        "",
    ]
    return "\n".join(lines)


def _build_powershell_start_command(bat_path: str) -> str:
    """Build a quoted PowerShell command that starts a .bat path via cmd.exe."""
    escaped_path = str(bat_path).replace("'", "''")
    return (
        "Start-Process -WindowStyle Hidden -FilePath 'cmd.exe' "
        f"-ArgumentList '/d', '/c', '\"\"{escaped_path}\"\"'"
    )


def _run_replace_script(current_exe: str, new_exe_name: str, base_dir: str, parent=None) -> None:
    current_exe_name = os.path.basename(current_exe)
    new_exe_path = os.path.join(base_dir, new_exe_name)
    bat_path = os.path.join(base_dir, "updater_pyqt6.bat")

    # cp866: только ASCII-кавычки. Кривые ” ломают запись bat и оставляют мусор на диске.
    content = _build_replace_bat_content(
        current_exe=current_exe,
        new_exe_path=new_exe_path,
        current_exe_name=current_exe_name,
    )
    with open(bat_path, "w", encoding="cp866", newline="\r\n") as f:
        f.write(content)

    QMessageBox.information(
        parent,
        "Обновление",
        "Обновление скачано. Сейчас приложение перезапустится и обновится.",
    )

    # Запускаем батник скрыто, чтобы не мелькало окно консоли.
    try:
        CREATE_NO_WINDOW = 0x08000000
        subprocess.Popen(
            [
                "powershell",
                "-NoProfile",
                "-WindowStyle",
                "Hidden",
                "-Command",
                _build_powershell_start_command(bat_path),
            ],
            creationflags=CREATE_NO_WINDOW,
        )
    except Exception:
        subprocess.Popen(f'start "" "{bat_path}"', shell=True)

    os._exit(0)

