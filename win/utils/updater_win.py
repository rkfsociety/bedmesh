import requests, os, sys, subprocess, threading
from tkinter import messagebox

REPO = "rkfsociety/bedmesh"

def check_for_updates(current_version, update_callback):
    def task():
        try:
            r = requests.get(f"https://api.github.com/repos/{REPO}/releases/latest", timeout=5)
            if r.status_code == 200:
                data = r.json()
                latest_tag = data.get("tag_name", "").replace("v", "")
                
                # Сравнение версий
                if latest_tag.split('-')[0] > current_version.split('-')[0]:
                    if any(a["name"].endswith(".exe") for a in data.get("assets", [])):
                        update_callback(latest_tag, data)
        except: 
            pass
    threading.Thread(target=task, daemon=True).start()

def install_update(data):
    try:
        url = next((a["browser_download_url"] for a in data["assets"] if a["name"].endswith(".exe")), None)
        if not url: return
        
        r = requests.get(url, stream=True)
        new_exe_name = "Bed_Mesh_Update_Temp.exe"
        
        # Определяем рабочую директорию (там, где лежит запущенный exe)
        base_dir = os.path.dirname(sys.executable)
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
            f.write(f':loop\n')
            f.write(f'tasklist | find /i "{current_exe_name}" > nul\n')
            f.write(f'if %errorlevel% equ 0 (timeout /t 1 > nul & goto loop)\n')
            f.write(f'del /f /q "{current_exe}"\n')
            f.write(f'move /y "{new_exe_name}" "{current_exe}"\n')
            f.write(f'start "" "{current_exe}"\n')
            f.write(f'del "%~f0"\n')
            
        messagebox.showinfo("Update", "Загрузка завершена. Программа будет перезапущена для обновления.")
        subprocess.Popen(bat_path, shell=True)
        os._exit(0)
    except Exception as e: 
        messagebox.showerror("Update Error", f"Не удалось установить обновление: {str(e)}")