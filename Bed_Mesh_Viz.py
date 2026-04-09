import tkinter as tk
from tkinter import scrolledtext, messagebox, ttk
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
import matplotlib.patheffects as path_effects
import numpy as np
import re
import paramiko
import json
import os
import requests
import threading
import sys
import subprocess
import time

# --- КОНСТАНТЫ ---
VERSION = "4.6"
REPO = "rkfsociety/bedmesh"
SETTINGS_FILE = "settings.json"

class TableVisualizer:
    def __init__(self, root):
        self.root = root
        self.root.title(f"Bed Mesh Visualizer Pro v{VERSION}")
        self.root.geometry("800x800")

        # Очистка мусора после предыдущих обновлений
        self.cleanup_old_files()

        self.settings = self.load_settings()

        # Статус обновления
        self.update_status = tk.Label(root, text="Проверка обновлений...", fg="gray", font=("Arial", 8))
        self.update_status.pack(side="top", anchor="e", padx=10)
        threading.Thread(target=self.check_updates, daemon=True).start()

        # --- ИНТЕРФЕЙС (SSH и конфиг) ---
        ssh_frame = tk.LabelFrame(root, text=" SSH Подключение ", padx=5, pady=5)
        ssh_frame.pack(fill="x", padx=10, pady=5)

        tk.Label(ssh_frame, text="IP:").grid(row=0, column=0)
        self.ssh_host = tk.Entry(ssh_frame, width=12); self.ssh_host.insert(0, self.settings.get("host", "192.168.1.100")); self.ssh_host.grid(row=0, column=1)
        tk.Label(ssh_frame, text="Порт:").grid(row=0, column=2)
        self.ssh_port = tk.Entry(ssh_frame, width=5); self.ssh_port.insert(0, self.settings.get("port", "22")); self.ssh_port.grid(row=0, column=3)
        tk.Label(ssh_frame, text="User:").grid(row=0, column=4)
        self.ssh_user = tk.Entry(ssh_frame, width=8); self.ssh_user.insert(0, self.settings.get("user", "pi")); self.ssh_user.grid(row=0, column=5)
        tk.Label(ssh_frame, text="Pass:").grid(row=0, column=6)
        self.ssh_pass = tk.Entry(ssh_frame, width=8, show="*"); self.ssh_pass.insert(0, self.settings.get("password", "raspberry")); self.ssh_pass.grid(row=0, column=7)

        self.cfg_path = tk.Entry(ssh_frame, width=40); self.cfg_path.insert(0, self.settings.get("path", "/home/pi/printer_data/config/printer_mutable.cfg")); self.cfg_path.grid(row=1, column=0, columnspan=6, pady=5, padx=5, sticky="w")
        tk.Button(ssh_frame, text="ВЫТЯНУТЬ", command=self.fetch_ssh, bg="#2196F3", fg="white", font=("Arial", 8, "bold")).grid(row=1, column=6, columnspan=2)

        cfg_frame = tk.LabelFrame(root, text=" Конфигурация стола ", padx=5, pady=5)
        cfg_frame.pack(fill="x", padx=10, pady=5)

        fields = [("bed_x", "250", 0, 1), ("bed_y", "250", 0, 2), ("grid_x", "5", 0, 4), ("grid_y", "5", 0, 5),
                  ("min_x", "5", 1, 1), ("min_y", "5", 1, 2), ("max_x", "245", 1, 4), ("max_y", "245", 1, 5)]
        self.entries = {}
        for key, default, r, c in fields:
            e = tk.Entry(cfg_frame, width=5); e.insert(0, self.settings.get(key, default)); e.grid(row=r, column=c)
            self.entries[key] = e

        self.screw_pitch = ttk.Combobox(cfg_frame, values=[0.7, 0.5, 0.8], width=5); self.screw_pitch.set(self.settings.get("pitch", 0.7)); self.screw_pitch.grid(row=1, column=6, padx=5)
        tk.Button(cfg_frame, text="💾", command=self.save_settings, bg="#FF9800", fg="white", font=("Arial", 8)).grid(row=0, column=6, padx=5)

        self.text_area = scrolledtext.ScrolledText(root, width=90, height=22, font=("Consolas", 9)); self.text_area.pack(padx=10, pady=5)

        btn_box = tk.Frame(root); btn_box.pack(pady=10)
        tk.Button(btn_box, text="3D ВИД (мм)", command=lambda: self.visualize("3d"), bg="#4CAF50", fg="white", width=25).grid(row=0, column=0, padx=5)
        tk.Button(btn_box, text="2D КАРТА + ВИНТЫ", command=lambda: self.visualize("2d"), bg="#9C27B0", fg="white", width=25).grid(row=0, column=1, padx=5)

    def cleanup_old_files(self):
        """Удаляет временные файлы обновлений при запуске"""
        for f in ["updater.bat", "Bed_Mesh_Viz_new.exe"]:
            if os.path.exists(f):
                try: os.remove(f)
                except: pass

    # --- ОБНОВЛЕННАЯ ЛОГИКА ОБНОВЛЕНИЯ ---
    def check_updates(self):
        try:
            r = requests.get(f"https://api.github.com/repos/{REPO}/releases/latest", timeout=5)
            data = r.json()
            latest = data.get("tag_name", "").replace("v", "")
            if latest and latest > VERSION:
                self.update_status.config(text=f"Доступно обновление v{latest}", fg="green")
                if messagebox.askyesno("Обновление", f"Найдена версия v{latest}. Обновить сейчас?"):
                    threading.Thread(target=self.download_update, args=(data,), daemon=True).start()
            else: self.update_status.config(text="Версия актуальна", fg="blue")
        except: self.update_status.config(text="Ошибка обновлений", fg="red")

    def download_update(self, data):
        url = next((a["browser_download_url"] for a in data["assets"] if a["name"].endswith(".exe")), None)
        if not url: return

        # Создаем окно прогресса
        progress_win = tk.Toplevel(self.root)
        progress_win.title("Загрузка...")
        progress_win.geometry("300x100")
        tk.Label(progress_win, text="Скачивание новой версии...").pack(pady=10)
        progress_bar = ttk.Progressbar(progress_win, length=200, mode='determinate')
        progress_bar.pack(pady=5)

        try:
            r = requests.get(url, stream=True)
            total_size = int(r.headers.get('content-length', 0))
            downloaded = 0
            new_exe = "Bed_Mesh_Viz_new.exe"
            
            with open(new_exe, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        progress_bar['value'] = (downloaded / total_size) * 100
                        progress_win.update()

            progress_win.destroy()
            self.install_update(new_exe)
        except Exception as e:
            progress_win.destroy()
            messagebox.showerror("Ошибка загрузки", str(e))

    def install_update(self, new_exe):
        # Определяем текущее имя файла (оно может отличаться от Bed_Mesh_Viz.exe)
        current_exe = os.path.abspath(sys.executable)
        current_name = os.path.basename(current_exe)
        
        # Создаем батник с циклом ожидания закрытия процесса
        with open("updater.bat", "w", encoding="cp866") as f:
            f.write(f'@echo off\n')
            f.write(f'title Updater\n')
            f.write(f'echo Ожидание закрытия программы...\n')
            f.write(f':loop\n')
            # Проверяем, запущен ли процесс
            f.write(f'tasklist | find /i "{current_name}" > nul\n')
            f.write(f'if %errorlevel% equ 0 (timeout /t 1 > nul & goto loop)\n')
            f.write(f'echo Замена файлов...\n')
            f.write(f'del /f /q "{current_exe}"\n')
            f.write(f'move /y "{new_exe}" "{current_exe}"\n')
            f.write(f'echo Запуск новой версии...\n')
            f.write(f'start "" "{current_exe}"\n')
            f.write(f'exit\n')
        
        messagebox.showinfo("Готово", "Загрузка завершена. Программа перезапустится для обновления.")
        subprocess.Popen("updater.bat", shell=True)
        self.root.quit()

    # --- ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ ---
    def load_settings(self):
        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE, "r") as f: return json.load(f)
            except: return {}
        return {}

    def save_settings(self, silent=False):
        d = {k: e.get() for k, e in self.entries.items()}
        d.update({"host": self.ssh_host.get(), "port": self.ssh_port.get(), "user": self.ssh_user.get(), 
                  "password": self.ssh_pass.get(), "path": self.cfg_path.get(), "pitch": self.screw_pitch.get()})
        with open(SETTINGS_FILE, "w") as f: json.dump(d, f, indent=4)
        if not silent: messagebox.showinfo("Успех", "Настройки сохранены!")

    def fetch_ssh(self):
        try:
            client = paramiko.SSHClient(); client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            client.connect(self.ssh_host.get(), int(self.ssh_port.get()), self.ssh_user.get(), self.ssh_pass.get(), timeout=10)
            sftp = client.open_sftp()
            with sftp.open(self.cfg_path.get(), 'r') as f: content = f.read().decode('utf-8')
            sftp.close(); client.close()
            self.text_area.delete("1.0", tk.END); self.text_area.insert(tk.END, content)
            try:
                js = json.loads(content).get("bed_mesh default", {})
                if js:
                    for k in ["x_count", "y_count", "min_x", "max_x", "min_y", "max_y"]:
                        if k in js:
                            key = k.replace("_count", "") if "_count" in k else k
                            entry_key = "grid_"+key[0] if "count" in k else k
                            self.entries[entry_key].delete(0, tk.END); self.entries[entry_key].insert(0, str(js[k]))
            except: pass
            self.save_settings(True)
        except Exception as e: messagebox.showerror("SSH Error", str(e))

    def visualize(self, mode):
        text = self.text_area.get("1.0", tk.END).strip()
        mesh_points_str = text
        try:
            data_json = json.loads(text)
            mesh_points_str = data_json.get("bed_mesh default", {}).get("points", text)
        except:
            match = re.search(r"points\s*=\s*([\s\S]+?)(?=\n\w|\Z)", text)
            if match: mesh_points_str = match.group(1)

        nums = [float(n) for n in re.findall(r"[-+]?\d*\.\d+|\d+", mesh_points_str)]
        gx, gy = int(self.entries["grid_x"].get()), int(self.entries["grid_y"].get())
        if len(nums) < gx * gy: return
        matrix = np.array(nums[:gx*gy]).reshape((gy, gx))
        for i in range(len(matrix)):
            if i % 2 != 0: matrix[i] = matrix[i][::-1]

        self.save_settings(True)
        plt.close('all')
        fig = plt.figure(figsize=(8, 8)) 
        mx, Mx = float(self.entries["min_x"].get()), float(self.entries["max_x"].get())
        my, My = float(self.entries["min_y"].get()), float(self.entries["max_y"].get())
        bx, by = float(self.entries["bed_x"].get()), float(self.entries["bed_y"].get())

        if mode == "3d":
            fig.canvas.manager.set_window_title("3D Вид")
            ax = fig.add_subplot(111, projection='3d')
            X, Y = np.meshgrid(np.linspace(mx, Mx, gx), np.linspace(my, My, gy))
            surf = ax.plot_surface(X, Y, matrix, cmap='RdYlBu_r', edgecolor='black', alpha=0.8)
            ax.set_xlim(0, bx); ax.set_ylim(0, by); fig.colorbar(surf, shrink=0.5, aspect=10)
        else:
            fig.canvas.manager.set_window_title("2D Карта")
            ax = fig.add_subplot(111)
            x_edges = np.linspace(0, bx, gx + 1); y_edges = np.linspace(0, by, gy + 1)
            x_centers = (x_edges[:-1] + x_edges[1:]) / 2; y_centers = (y_edges[:-1] + y_edges[1:]) / 2
            im = ax.pcolormesh(x_edges, y_edges, matrix, cmap='RdYlBu_r', edgecolors='black', linewidth=1)
            ax.set_xlim(0, bx); ax.set_ylim(0, by); ax.set_aspect('equal')
            for i in range(gy):
                for j in range(gx):
                    txt = ax.text(x_centers[j], y_centers[i], f"{matrix[i,j]:.3f}", ha="center", va="center", fontweight='bold', fontsize=9)
                    txt.set_path_effects([path_effects.withStroke(linewidth=2, foreground="white")])
            corners = {"ПЛ": matrix[0,0], "ПП": matrix[0,-1], "ЗЛ": matrix[-1,0], "ЗП": matrix[-1,-1]}
            base, p = min(corners.values()), float(self.screw_pitch.get())
            instr = "\n".join([f"{k}: {v-base:+.3f}мм ({(v-base)/p:.2f} об. {'ВНИЗ' if v-base>0 else 'ОК'})" for k,v in corners.items()])
            plt.gcf().text(0.12, 0.02, f"Винты:\n{instr}", fontsize=9, bbox=dict(facecolor='white', alpha=0.7))
            fig.colorbar(im)
        plt.tight_layout(); plt.show()

if __name__ == "__main__":
    root = tk.Tk(); app = TableVisualizer(root); root.mainloop()