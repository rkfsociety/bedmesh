import os
import re
import sys
import subprocess
import threading
import webbrowser
from typing import Callable, Optional, Tuple

import requests
from PyQt6.QtWidgets import QMessageBox, QProgressDialog
from PyQt6.QtCore import QTimer, Qt


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
                r = requests.get(url, stream=True, timeout=30)
                r.raise_for_status()
                total = int(r.headers.get("Content-Length") or 0)
                if total > 0:
                    state["total"] = total
                with open(new_exe_path, "wb") as f:
                    for chunk in r.iter_content(chunk_size=1024 * 256):
                        if not chunk:
                            continue
                        f.write(chunk)
                        state["bytes"] += len(chunk)
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


def _run_replace_script(current_exe: str, new_exe_name: str, base_dir: str, parent=None) -> None:
    current_exe_name = os.path.basename(current_exe)
    bat_path = os.path.join(base_dir, "updater_pyqt6.bat")

    with open(bat_path, "w", encoding="cp866") as f:
        f.write("@echo off\n")
        f.write("setlocal\n")
        f.write("set tries=0\n")
        f.write(f'taskkill /f /im "{current_exe_name}" >nul 2>&1\n')
        f.write("timeout /t 4 /nobreak > nul\n")
        f.write(":loop\n")
        f.write(f'del /f /q \"{current_exe}\" >nul 2>&1\n')
        f.write(f'if exist \"{current_exe}\" (timeout /t 1 /nobreak > nul & goto loop)\n')
        f.write(f'move /y \"{new_exe_name}\" \"{current_exe}\" >nul\n')
        # Важно для PyInstaller onefile:
        # переносим TEMP/TMP в стабильную папку, чтобы распаковка _MEI и python310.dll
        # не ломалась из-за очистки/блокировок системного %TEMP%.
        f.write("set \"APP_TMP=%LOCALAPPDATA%\\rkfsociety\\BedMesh Visualizer\\tmp\"\n")
        f.write("if not exist \"%APP_TMP%\" mkdir \"%APP_TMP%\" >nul 2>&1\n")
        f.write("set \"TEMP=%APP_TMP%\"\n")
        f.write("set \"TMP=%APP_TMP%\"\n")
        # Небольшая пауза, чтобы ОС/антивирус успели “подхватить” новый exe до старта.
        f.write("timeout /t 3 /nobreak > nul\n")
        f.write(":startloop\n")
        # Пытаемся стартовать несколько раз — иногда сразу после замены exe может быть временная блокировка.
        f.write("set \"RUNNING=\"\n")
        f.write(f'start \"\" \"{current_exe}\" >nul 2>&1\n')
        f.write("timeout /t 2 /nobreak > nul\n")
        f.write(f'for /f \"tokens=*\" %%p in (\'tasklist /fi \"imagename eq {current_exe_name}\" ^| find /i \"{current_exe_name}\" \') do set RUNNING=1\n')
        f.write("if defined RUNNING goto started\n")
        f.write("set /a tries+=1\n")
        f.write("if %tries% GEQ 6 goto started\n")
        f.write("goto startloop\n")
        f.write(":started\n")
        f.write("endlocal\n")
        f.write('del "%~f0"\n')

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
                f"Start-Process -WindowStyle Hidden -FilePath 'cmd.exe' -ArgumentList '/c', '{bat_path}'",
            ],
            creationflags=CREATE_NO_WINDOW,
        )
    except Exception:
        subprocess.Popen(f'start "" "{bat_path}"', shell=True)

    os._exit(0)

