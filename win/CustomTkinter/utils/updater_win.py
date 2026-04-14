import requests, os, sys, subprocess, threading
from tkinter import messagebox

# Твой репозиторий
REPO = "rkfsociety/bedmesh"

def is_new_version(current, remote):
    """
    Корректно сравнивает версии по числам (например, 0.151 > 0.150).
    Игнорирует буквы и суффиксы.
    """
    try:
        # Очистка строк от лишних символов
        c_clean = current.lower().replace('v', '').split('-')[0]
        r_clean = remote.lower().replace('v', '').split('-')[0]
        
        c_parts = [int(p) for p in c_clean.split('.')]
        r_parts = [int(p) for p in r_clean.split('.')]
        
        # Дополняем списки нулями до одинаковой длины
        max_len = max(len(c_parts), len(r_parts))
        c_parts += [0] * (max_len - len(c_parts))
        r_parts += [0] * (max_len - len(r_parts))
        
        return r_parts > c_parts
    except Exception:
        # Если что-то пошло не так, пробуем простое сравнение строк
        return remote > current

def check_for_updates(current_version, update_callback):
    """
    Проверка обновлений в отдельном потоке.
    """
    def task():
        try:
            r = requests.get(f"https://api.github.com/repos/{REPO}/releases/latest", timeout=5)
            if r.status_code == 200:
                data = r.json()
                latest_tag = data.get("tag_name", "") # Например, 'v0.151-win'
                
                # ФИЛЬТР ПЛАТФОРМЫ:
                # Если мы на Windows, а в теге есть '-mac' и нет '-win', пропускаем.
                if "-mac" in latest_tag.lower() and "-win" not in latest_tag.lower():
                    return

                # Сравнение версий
                if is_new_version(current_version, latest_tag):
                    # Проверяем наличие .exe в ассетах релиза
                    if any(a["name"].endswith(".exe") for a in data.get("assets", [])):
                        update_callback(latest_tag, data)
        except Exception: 
            pass
            
    threading.Thread(target=task, daemon=True).start()

def install_update(data):
    """
    Процесс скачивания и запуска батника для замены файла.
    """
    try:
        # Ищем прямую ссылку на .exe файл среди ассетов
        url = next((a["browser_download_url"] for a in data["assets"] if a["name"].endswith(".exe")), None)
        if not url: 
            return
        
        r = requests.get(url, stream=True)
        new_exe_name = "Bed_Mesh_Update_Temp.exe"
        
        # Определяем пути (используем abspath для исключения ошибок доступа)
        base_dir = os.path.dirname(os.path.abspath(sys.executable))
        new_exe_path = os.path.join(base_dir, new_exe_name)
        
        # Скачивание нового файла
        with open(new_exe_path, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192): 
                if chunk:
                    f.write(chunk)
        
        current_exe = os.path.abspath(sys.executable)
        current_exe_name = os.path.basename(current_exe)
        bat_path = os.path.join(base_dir, "updater_win.bat")
        
        # Создание усиленного батника для решения проблемы "PermissionError"
        with open(bat_path, "w", encoding="cp866") as f:
            f.write(f'@echo off\n')
            f.write(f'title Updating Bed Mesh Visualizer...\n')
            f.write(f'echo Closing process {current_exe_name}...\n')
            
            # Принудительно завершаем процесс, если он еще жив
            f.write(f'taskkill /f /im "{current_exe_name}" >nul 2>&1\n')
            f.write(f'timeout /t 2 /nobreak > nul\n')
            
            f.write(f':loop\n')
            # Пытаемся удалить старый файл. Если он занят - del вернет ошибку, и мы подождем.
            f.write(f'del /f /q "{current_exe}" >nul 2>&1\n')
            f.write(f'if exist "{current_exe}" (timeout /t 1 /nobreak > nul & goto loop)\n')
            
            f.write(f'echo Installing new version...\n')
            f.write(f'move /y "{new_exe_name}" "{current_exe}" >nul\n')
            f.write(f'echo Starting application...\n')
            f.write(f'start "" "{current_exe}"\n')
            f.write(f'del "%~f0"\n')
            
        messagebox.showinfo("Update", "Загрузка завершена. Программа закроется на несколько секунд для установки обновления.")
        
        # Запускаем батник через команду start, чтобы он не зависел от родительского процесса
        subprocess.Popen(f'start "" "{bat_path}"', shell=True)
        os._exit(0)
        
    except Exception as e: 
        messagebox.showerror("Update Error", f"Не удалось установить обновление: {str(e)}")