import requests, os, sys, subprocess, threading
from tkinter import messagebox

REPO = "rkfsociety/bedmesh"

def check_for_updates(current_version, update_callback):
    def task():
        try:
            r = requests.get(f"https://api.github.com/repos/{REPO}/releases/latest", timeout=5)
            if r.status_code == 200:
                data = r.json()
                latest_v = data.get("tag_name", "").replace("v", "")
                if latest_v > current_version: update_callback(latest_v, data)
        except: pass
    threading.Thread(target=task, daemon=True).start()

def install_update(data):
    try:
        assets = data.get("assets", [])
        url = next((a["browser_download_url"] for a in assets if a["name"].endswith(".exe")), None)
        if not url: return
        r = requests.get(url, stream=True)
        with open("Bed_Mesh_Viz_new.exe", 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192): f.write(chunk)
        
        current_exe = os.path.abspath(sys.executable)
        with open("updater.bat", "w", encoding="cp866") as f:
            f.write(f'@echo off\n:loop\ntasklist | find /i "{os.path.basename(current_exe)}" > nul\n')
            f.write(f'if %errorlevel% equ 0 (timeout /t 1 > nul & goto loop)\n')
            f.write(f'del /f /q "{current_exe}"\nmove /y "Bed_Mesh_Viz_new.exe" "{current_exe}"\n')
            f.write(f'start "" "{current_exe}"\ndel "%~f0"\n')
        
        messagebox.showinfo("Update", "Обновление скачано. Перезапуск...")
        subprocess.Popen("updater.bat", shell=True)
        os._exit(0)
    except Exception as e: messagebox.showerror("Error", str(e))