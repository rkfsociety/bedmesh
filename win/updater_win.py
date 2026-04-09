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
                if latest_tag.split('-')[0] > current_version.split('-')[0]:
                    if any(a["name"].endswith(".exe") for a in data.get("assets", [])):
                        update_callback(latest_tag, data)
        except: pass
    threading.Thread(target=task, daemon=True).start()

def install_update(data):
    try:
        url = next((a["browser_download_url"] for a in data["assets"] if a["name"].endswith(".exe")), None)
        if not url: return
        r = requests.get(url, stream=True)
        new_exe = "Bed_Mesh_Viz_Win_new.exe"
        with open(new_exe, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192): f.write(chunk)
        current_exe = os.path.abspath(sys.executable)
        with open("updater_win.bat", "w", encoding="cp866") as f:
            f.write(f'@echo off\n:loop\ntasklist | find /i "{os.path.basename(current_exe)}" > nul\n')
            f.write(f'if %errorlevel% equ 0 (timeout /t 1 > nul & goto loop)\n')
            f.write(f'del /f /q "{current_exe}"\nmove /y "{new_exe}" "{current_exe}"\n')
            f.write(f'start "" "{current_exe}"\ndel "%~f0"\n')
        messagebox.showinfo("Update", "Перезапуск..."); subprocess.Popen("updater_win.bat", shell=True); os._exit(0)
    except Exception as e: messagebox.showerror("Update Error", str(e))