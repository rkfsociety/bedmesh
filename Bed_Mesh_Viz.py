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

# --- КОНСТАНТЫ ---
VERSION = "4.5"
REPO = "rkfsociety/bedmesh"
SETTINGS_FILE = "settings.json"

class TableVisualizer:
    def __init__(self, root):
        self.root = root
        self.root.title(f"Bed Mesh Visualizer Pro v{VERSION}")
        self.root.geometry("800x800")

        self.settings = self.load_settings()

        self.update_status = tk.Label(root, text="Проверка обновлений...", fg="gray", font=("Arial", 8))
        self.update_status.pack(side="top", anchor="e", padx=10)
        threading.Thread(target=self.check_updates, daemon=True).start()

        # --- SSH ПАНЕЛЬ ---
        ssh_frame = tk.LabelFrame(root, text=" SSH Подключение ", padx=5, pady=5)
        ssh_frame.pack(fill="x", padx=10, pady=5)

        tk.Label(ssh_frame, text="IP:").grid(row=0, column=0)
        self.ssh_host = tk.Entry(ssh_frame, width=12)
        self.ssh_host.insert(0, self.settings.get("host", "192.168.1.100"))
        self.ssh_host.grid(row=0, column=1)

        tk.Label(ssh_frame, text="Порт:").grid(row=0, column=2)
        self.ssh_port = tk.Entry(ssh_frame, width=5)
        self.ssh_port.insert(0, self.settings.get("port", "22"))
        self.ssh_port.grid(row=0, column=3)

        tk.Label(ssh_frame, text="User:").grid(row=0, column=4)
        self.ssh_user = tk.Entry(ssh_frame, width=8)
        self.ssh_user.insert(0, self.settings.get("user", "pi"))
        self.ssh_user.grid(row=0, column=5)

        tk.Label(ssh_frame, text="Pass:").grid(row=0, column=6)
        self.ssh_pass = tk.Entry(ssh_frame, width=8, show="*")
        self.ssh_pass.insert(0, self.settings.get("password", "raspberry"))
        self.ssh_pass.grid(row=0, column=7)

        self.cfg_path = tk.Entry(ssh_frame, width=40)
        self.cfg_path.insert(0, self.settings.get("path", "/home/pi/printer_data/config/printer_mutable.cfg"))
        self.cfg_path.grid(row=1, column=0, columnspan=6, pady=5, padx=5, sticky="w")

        self.btn_ssh = tk.Button(ssh_frame, text="ВЫТЯНУТЬ", command=self.fetch_ssh, bg="#2196F3", fg="white", font=("Arial", 8, "bold"))
        self.btn_ssh.grid(row=1, column=6, columnspan=2)

        # --- ПАРАМЕТРЫ СЕТКИ ---
        cfg_frame = tk.LabelFrame(root, text=" Конфигурация стола ", padx=5, pady=5)
        cfg_frame.pack(fill="x", padx=10, pady=5)

        tk.Label(cfg_frame, text="Стол X/Y:").grid(row=0, column=0)
        self.bed_x = tk.Entry(cfg_frame, width=5); self.bed_x.insert(0, self.settings.get("bed_x", "250"))
        self.bed_x.grid(row=0, column=1)
        self.bed_y = tk.Entry(cfg_frame, width=5); self.bed_y.insert(0, self.settings.get("bed_y", "250"))
        self.bed_y.grid(row=0, column=2)

        tk.Label(cfg_frame, text="Точки X/Y:").grid(row=0, column=3)
        self.entry_x = tk.Entry(cfg_frame, width=3); self.entry_x.insert(0, self.settings.get("grid_x", "5"))
        self.entry_x.grid(row=0, column=4)
        self.entry_y = tk.Entry(cfg_frame, width=3); self.entry_y.insert(0, self.settings.get("grid_y", "5"))
        self.entry_y.grid(row=0, column=5)

        tk.Label(cfg_frame, text="Min X/Y:").grid(row=1, column=0)
        self.min_x = tk.Entry(cfg_frame, width=5); self.min_x.insert(0, self.settings.get("min_x", "5"))
        self.min_x.grid(row=1, column=1)
        self.min_y = tk.Entry(cfg_frame, width=5); self.min_y.insert(0, self.settings.get("min_y", "5"))
        self.min_y.grid(row=1, column=2)

        tk.Label(cfg_frame, text="Max X/Y:").grid(row=1, column=3)
        self.max_x = tk.Entry(cfg_frame, width=5); self.max_x.insert(0, self.settings.get("max_x", "245"))
        self.max_x.grid(row=1, column=4)
        self.max_y = tk.Entry(cfg_frame, width=5); self.max_y.insert(0, self.settings.get("max_y", "245"))
        self.max_y.grid(row=1, column=5)

        self.screw_pitch = ttk.Combobox(cfg_frame, values=[0.7, 0.5, 0.8], width=5)
        self.screw_pitch.set(self.settings.get("pitch", 0.7))
        self.screw_pitch.grid(row=1, column=6, padx=5)

        self.btn_manual_save = tk.Button(cfg_frame, text="💾", command=self.save_settings, bg="#FF9800", fg="white", font=("Arial", 8))
        self.btn_manual_save.grid(row=0, column=6, padx=5)

        # --- ПОЛЕ ДАННЫХ ---
        self.text_area = scrolledtext.ScrolledText(root, width=90, height=22, font=("Consolas", 9))
        self.text_area.pack(padx=10, pady=5)

        btn_box = tk.Frame(root)
        btn_box.pack(pady=10)
        tk.Button(btn_box, text="3D ВИД (мм)", command=lambda: self.visualize("3d"), bg="#4CAF50", fg="white", width=25).grid(row=0, column=0, padx=5)
        tk.Button(btn_box, text="2D КАРТА + ВИНТЫ", command=lambda: self.visualize("2d"), bg="#9C27B0", fg="white", width=25).grid(row=0, column=1, padx=5)

    def check_updates(self):
        try:
            r = requests.get(f"https://api.github.com/repos/{REPO}/releases/latest", timeout=5)
            latest = r.json().get("tag_name", "").replace("v", "")
            if latest and latest > VERSION:
                self.update_status.config(text=f"Доступно обновление v{latest}", fg="green")
                if messagebox.askyesno("Обновление", f"Найдена версия v{latest}. Обновить?"):
                    self.download_update(r.json())
            else: self.update_status.config(text="Версия актуальна", fg="blue")
        except: self.update_status.config(text="Ошибка обновлений", fg="red")

    def download_update(self, data):
        url = next((a["browser_download_url"] for a in data["assets"] if a["name"].endswith(".exe")), None)
        if not url: return
        r = requests.get(url)
        with open("Bed_Mesh_Viz_new.exe", 'wb') as f: f.write(r.content)
        with open("updater.bat", "w") as f:
            f.write(f'@echo off\ntimeout /t 2\ndel "{os.path.basename(sys.executable)}"\nren "Bed_Mesh_Viz_new.exe" "{os.path.basename(sys.executable)}"\nstart "" "{os.path.basename(sys.executable)}"\ndel updater.bat')
        subprocess.Popen("updater.bat", shell=True); self.root.destroy()

    def fetch_ssh(self):
        try:
            client = paramiko.SSHClient(); client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            client.connect(self.ssh_host.get(), int(self.ssh_port.get()), self.ssh_user.get(), self.ssh_pass.get())
            sftp = client.open_sftp()
            with sftp.open(self.cfg_path.get(), 'r') as f: content = f.read().decode('utf-8')
            sftp.close(); client.close()
            self.text_area.delete("1.0", tk.END); self.text_area.insert(tk.END, content)
            try:
                js = json.loads(content).get("bed_mesh default", {})
                if js:
                    for k, e in [("x_count", self.entry_x), ("y_count", self.entry_y), ("min_x", self.min_x), ("max_x", self.max_x), ("min_y", self.min_y), ("max_y", self.max_y)]:
                        e.delete(0, tk.END); e.insert(0, js.get(k, ""))
            except: pass
            self.save_settings(True)
        except Exception as e: messagebox.showerror("SSH Error", str(e))

    def load_settings(self):
        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE, "r") as f: return json.load(f)
            except: return {}
        return {}

    def save_settings(self, silent=False):
        d = {"host": self.ssh_host.get(), "port": self.ssh_port.get(), "user": self.ssh_user.get(), "password": self.ssh_pass.get(), "path": self.cfg_path.get(), "bed_x": self.bed_x.get(), "bed_y": self.bed_y.get(), "grid_x": self.entry_x.get(), "grid_y": self.entry_y.get(), "min_x": self.min_x.get(), "max_x": self.max_x.get(), "min_y": self.min_y.get(), "max_y": self.max_y.get(), "pitch": self.screw_pitch.get()}
        with open(SETTINGS_FILE, "w") as f: json.dump(d, f, indent=4)
        if not silent: messagebox.showinfo("Успех", "Настройки сохранены!")

    def visualize(self, mode):
        text = self.text_area.get("1.0", tk.END).strip()
        
        # Парсим точки из JSON или текста
        mesh_points_str = text
        try:
            data_json = json.loads(text)
            mesh_points_str = data_json.get("bed_mesh default", {}).get("points", text)
        except:
            match = re.search(r"points\s*=\s*([\s\S]+?)(?=\n\w|\Z)", text)
            if match: mesh_points_str = match.group(1)

        nums = [float(n) for n in re.findall(r"[-+]?\d*\.\d+|\d+", mesh_points_str)]
        gx, gy = int(self.entry_x.get()), int(self.entry_y.get())
        
        if len(nums) < gx * gy:
            messagebox.showerror("Ошибка", f"Найдено {len(nums)} точек, нужно {gx*gy}.")
            return
            
        # Формируем матрицу (Klipper закладывает по строкам)
        matrix = np.array(nums[:gx*gy]).reshape((gy, gx))
        
        # --- ЛОГИКА "ЗМЕЙКИ" (Serpentine Path) ---
        # Т.к. калибровка идет: L-R, затем R-L, затем L-R...
        # Каждую нечетную строку (индексы 1, 3, 5...) нужно развернуть обратно
        for i in range(len(matrix)):
            if i % 2 != 0:
                matrix[i] = matrix[i][::-1]

        self.save_settings(True)

        plt.close('all')
        fig = plt.figure(figsize=(8, 8)) 
        mx, Mx = float(self.min_x.get()), float(self.max_x.get())
        my, My = float(self.min_y.get()), float(self.max_y.get())
        bx, by = float(self.bed_x.get()), float(self.bed_y.get())

        if mode == "3d":
            fig.canvas.manager.set_window_title("3D Вид")
            ax = fig.add_subplot(111, projection='3d')
            X, Y = np.meshgrid(np.linspace(mx, Mx, gx), np.linspace(my, My, gy))
            surf = ax.plot_surface(X, Y, matrix, cmap='RdYlBu_r', edgecolor='black', alpha=0.8)
            ax.set_xlim(0, bx); ax.set_ylim(0, by)
            ax.set_xlabel("X (мм)"); ax.set_ylabel("Y (мм)"); ax.set_zlabel("Z (мм)")
            fig.colorbar(surf, shrink=0.5, aspect=10)
        else:
            fig.canvas.manager.set_window_title("2D Карта")
            ax = fig.add_subplot(111)
            x_edges = np.linspace(0, bx, gx + 1)
            y_edges = np.linspace(0, by, gy + 1)
            x_centers = (x_edges[:-1] + x_edges[1:]) / 2
            y_centers = (y_edges[:-1] + y_edges[1:]) / 2

            im = ax.pcolormesh(x_edges, y_edges, matrix, cmap='RdYlBu_r', edgecolors='black', linewidth=1)
            ax.set_xlim(0, bx); ax.set_ylim(0, by); ax.set_aspect('equal')
            
            for i in range(gy):
                for j in range(gx):
                    txt = ax.text(x_centers[j], y_centers[i], f"{matrix[i,j]:.3f}", 
                                ha="center", va="center", fontweight='bold', fontsize=9)
                    txt.set_path_effects([path_effects.withStroke(linewidth=2, foreground="white")])
            
            corners = {"ПЛ": matrix[0,0], "ПП": matrix[0,-1], "ЗЛ": matrix[-1,0], "ЗП": matrix[-1,-1]}
            base = min(corners.values())
            p = float(self.screw_pitch.get())
            instr = "\n".join([f"{k}: {v-base:+.3f}мм ({(v-base)/p:.2f} об. {'ВНИЗ' if v-base>0 else 'ОК'})" for k,v in corners.items()])
            plt.gcf().text(0.12, 0.02, f"Винты:\n{instr}", fontsize=9, bbox=dict(facecolor='white', alpha=0.7))
            fig.colorbar(im, label="Z (мм)")
            ax.set_xlabel("X (мм)"); ax.set_ylabel("Y (мм)")
        
        plt.tight_layout()
        plt.show()

if __name__ == "__main__":
    root = tk.Tk(); app = TableVisualizer(root); root.mainloop()