import requests, os, sys, subprocess, threading
from tkinter import messagebox

REPO = "rkfsociety/bedmesh"

def check_for_updates(current_version, update_callback):
    def task():
        try:
            r = requests.get(f"https://api.github.com/repos/{REPO}/releases/latest", timeout=5)
            if r.status_code == 200:
                data = r.json()
                latest_tag_raw = data.get("tag_name", "") # Например, 'v0.151-win'
                
                # ПРОВЕРКА ПЛАТФОРМЫ:
                # Если в теге на GitHub есть '-mac', а мы на Windows — игнорируем этот релиз
                if "-mac" in latest_tag_raw.lower() and "-win" not in latest_tag_raw.lower():
                    return

                # Очищаем теги для сравнения цифр
                latest_clean = latest_tag_raw.lower().replace('v', '').split('-')[0]
                current_clean = current_version.lower().replace('v', '').split('-')[0]
                
                # Сравнение как чисел (0.151 > 0.150)
                if is_new_version(current_clean, latest_clean):
                    # Проверяем, что в ассетах есть EXE (дополнительная страховка для Windows)
                    if any(a["name"].endswith(".exe") for a in data.get("assets", [])):
                        update_callback(latest_tag_raw, data)
        except: 
            pass
    threading.Thread(target=task, daemon=True).start()

def is_new_version(current, remote):
    """Сравнивает версии корректно (0.151 > 0.150)"""
    try:
        c_parts = [int(p) for p in current.split('.')]
        r_parts = [int(p) for p in remote.split('.')]
        max_len = max(len(c_parts), len(r_parts))
        c_parts += [0] * (max_len - len(c_parts))
        r_parts += [0] * (max_len - len(r_parts))
        return r_parts > c_parts
    except:
        return False

def install_update(data):
    try:
        # Ищем именно .exe ассет
        url = next((a["browser_download_url"] for a in data["assets"] if a["name"].endswith(".exe")), None)
        if not url: 
            return
        
        r = requests.get(url, stream=True)
        new_exe_name = "Bed_Mesh_Update_Temp.exe"
        
        base_dir = os.path.dirname(os.path.abspath(sys.executable))
        new_exe_path = os.path.join(base_dir, new_exe_name)
        
        with open(new_exe_path, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192): 
                f.write(chunk)
        
        current_exe = os.path.abspath(sys.executable)
        current_exe_name = os.path.basename(current_exe)
        bat_path = os.path.join(base_dir, "updater_win.bat")
        
        with open(bat_path, "w", encoding="cp866") as f:
            f.write(f'@echo off\n')
            f.write(f'title Updating Bed Mesh Visualizer...\n')
            f.write(f'echo Waiting for application to close...\n')
            f.write(f':loop\n')
            f.write(f'tasklist | find /i "{current_exe_name}" > nul\n')
            f.write(f'if %errorlevel% equ 0 (timeout /t 1 > nul & goto loop)\n')
            f.write(f'echo Installing new version...\n')
            f.write(f'del /f /q "{current_exe}"\n')
            f.write(f'move /y "{new_exe_name}" "{current_exe}"\n')
            f.write(f'echo Restarting...\n')
            f.write(f'start "" "{current_exe}"\n')
            f.write(f'del "%~f0"\n')
            
        messagebox.showinfo("Update", "Загрузка завершена. Программа будет обновлена и перезапущена.")
        subprocess.Popen(bat_path, shell=True)
        os._exit(0)
        
    except Exception as e: 
        messagebox.showerror("Update Error", f"Ошибка обновления: {str(e)}")