import requests
import os
import sys
import subprocess
import threading
from tkinter import messagebox

REPO = "rkfsociety/bedmesh"

def check_for_updates(current_version, update_callback):
    """
    Фоновая проверка обновлений.
    update_callback: функция из main.py, которая покажет кнопку или уведомление.
    """
    def task():
        try:
            r = requests.get(f"https://api.github.com/repos/{REPO}/releases/latest", timeout=5)
            if r.status_code == 200:
                data = r.json()
                latest_v = data.get("tag_name", "").replace("v", "")
                if latest_v > current_version:
                    # Если нашли обновление, передаем данные в callback
                    update_callback(latest_v, data)
        except Exception as e:
            print(f"Ошибка при проверке обновлений: {e}")

    thread = threading.Thread(target=task, daemon=True)
    thread.start()

def install_update(data):
    """ Скачивание и запуск процесса замены файла """
    try:
        # Ищем .exe в ассетах релиза
        assets = data.get("assets", [])
        download_url = next((a["browser_download_url"] for a in assets if a["name"].endswith(".exe")), None)
        
        if not download_url:
            messagebox.showerror("Ошибка", "Файл обновления .exe не найден в релизе.")
            return

        r = requests.get(download_url, stream=True)
        new_exe = "Bed_Mesh_Viz_new.exe"
        
        with open(new_exe, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)

        # Пути для батника
        current_exe = os.path.abspath(sys.executable)
        current_name = os.path.basename(current_exe)

        # Создаем батник для замены файла после закрытия программы
        with open("updater.bat", "w", encoding="cp866") as f:
            f.write(f'@echo off\n')
            f.write(f'title Updating Bed Mesh Visualizer...\n')
            f.write(f':loop\n')
            # Ждем, пока основной процесс закроется
            f.write(f'tasklist | find /i "{current_name}" > nul\n')
            f.write(f'if %errorlevel% equ 0 (timeout /t 1 > nul & goto loop)\n')
            # Заменяем файл
            f.write(f'del /f /q "{current_exe}"\n')
            f.write(f'move /y "{new_exe}" "{current_exe}"\n')
            # Запускаем обновленную версию
            f.write(f'start "" "{current_exe}"\n')
            f.write(f'del "%~f0"\n') # Самоудаление батника

        messagebox.showinfo("Обновление", "Обновление скачано. Программа будет перезапущена.")
        subprocess.Popen("updater.bat", shell=True)
        os._exit(0) # Немедленный выход

    except Exception as e:
        messagebox.showerror("Ошибка обновления", str(e))