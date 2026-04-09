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

# Имя файла для хранения настроек
SETTINGS_FILE = "settings.json"

class TableVisualizer:
    def __init__(self, root):
        self.root = root
        # Название программы строго по запросу
        self.root.title("Bed Mesh Visualizer Pro v4.0")
        self.root.geometry("850x950")

        # Загружаем настройки из файла
        self.settings = self.load_settings()

        # --- БЛОК SSH ПОДКЛЮЧЕНИЯ ---
        ssh_frame = tk.LabelFrame(root, text=" Подключение к принтеру (SSH) ", padx=10, pady=10)
        ssh_frame.pack(fill="x", padx=20, pady=5)

        tk.Label(ssh_frame, text="IP:").grid(row=0, column=0)
        self.ssh_host = tk.Entry(ssh_frame, width=15)
        self.ssh_host.insert(0, self.settings.get("host", "192.168.1.100"))
        self.ssh_host.grid(row=0, column=1, padx=5)

        tk.Label(ssh_frame, text="Порт:").grid(row=0, column=2)
        self.ssh_port = tk.Entry(ssh_frame, width=6)
        self.ssh_port.insert(0, self.settings.get("port", "22"))
        self.ssh_port.grid(row=0, column=3, padx=5)

        tk.Label(ssh_frame, text="User:").grid(row=0, column=4)
        self.ssh_user = tk.Entry(ssh_frame, width=10)
        self.ssh_user.insert(0, self.settings.get("user", "pi"))
        self.ssh_user.grid(row=0, column=5, padx=5)

        tk.Label(ssh_frame, text="Pass:").grid(row=0, column=6)
        self.ssh_pass = tk.Entry(ssh_frame, width=10, show="*")
        self.ssh_pass.insert(0, self.settings.get("password", "raspberry"))
        self.ssh_pass.grid(row=0, column=7, padx=5)

        tk.Label(ssh_frame, text="Путь к файлу:").grid(row=1, column=0, pady=10)
        self.cfg_path = tk.Entry(ssh_frame, width=50)
        self.cfg_path.insert(0, self.settings.get("path", "/home/pi/printer_data/config/printer_mutable.cfg"))
        self.cfg_path.grid(row=1, column=1, columnspan=5, sticky="w", padx=5)

        self.btn_ssh = tk.Button(ssh_frame, text="ВЫТЯНУТЬ CFG", command=self.fetch_ssh, bg="#2196F3", fg="white", font=("Arial", 9, "bold"))
        self.btn_ssh.grid(row=1, column=6, columnspan=2, padx=10)

        # --- НАСТРОЙКИ СЕТКИ И ВИНТОВ ---
        settings_frame = tk.LabelFrame(root, text=" Параметры стола и механики ", padx=10, pady=10)
        settings_frame.pack(fill="x", padx=20, pady=5)

        tk.Label(settings_frame, text="Размер X:").grid(row=0, column=0)
        self.bed_x = tk.Entry(settings_frame, width=5); self.bed_x.insert(0, self.settings.get("bed_x", "250"))
        self.bed_x.grid(row=0, column=1)

        tk.Label(settings_frame, text="Размер Y:").grid(row=0, column=2)
        self.bed_y = tk.Entry(settings_frame, width=5); self.bed_y.insert(0, self.settings.get("bed_y", "250"))
        self.bed_y.grid(row=0, column=3)

        tk.Label(settings_frame, text="Винты:").grid(row=0, column=4, padx=5)
        self.screw_pitch = ttk.Combobox(settings_frame, values=[0.7, 0.5, 0.8], width=10)
        self.screw_pitch.set(self.settings.get("pitch", 0.7))
        self.screw_pitch.grid(row=0, column=5)

        tk.Label(settings_frame, text="Точек X/Y:").grid(row=1, column=0, pady=5)
        self.entry_x = tk.Entry(settings_frame, width=5); self.entry_x.insert(0, self.settings.get("grid_x", "5"))
        self.entry_x.grid(row=1, column=1)
        self.entry_y = tk.Entry(settings_frame, width=5); self.entry_y.insert(0, self.settings.get("grid_y", "5"))
        self.entry_y.grid(row=1, column=3)

        self.btn_save = tk.Button(settings_frame, text="СОХРАНИТЬ КОНФИГ", command=self.save_settings, bg="#FF9800", fg="white")
        self.btn_save.grid(row=1, column=4, columnspan=2, padx=20)

        # --- ПОЛЕ ВВОДА ---
        self.text_area = scrolledtext.ScrolledText(root, width=95, height=15, font=("Consolas", 10))
        self.text_area.pack(padx=20, pady=5)

        # КНОПКИ ПОСТРОЕНИЯ
        btn_frame = tk.Frame(root)
        btn_frame.pack(pady=10)

        self.btn_plot_3d = tk.Button(btn_frame, text="3D ВИД", command=lambda: self.visualize("3d"), bg="#4CAF50", fg="white", width=20, font=("Arial", 10, "bold"))
        self.btn_plot_3d.grid(row=0, column=0, padx=10)

        self.btn_plot_2d = tk.Button(btn_frame, text="2D КАРТА + ВИНТЫ", command=lambda: self.visualize("2d"), bg="#9C27B0", fg="white", width=20, font=("Arial", 10, "bold"))
        self.btn_plot_2d.grid(row=0, column=1, padx=10)

    def load_settings(self):
        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE, "r") as f: return json.load(f)
            except: return {}
        return {}

    def save_settings(self, silent=False):
        data = {
            "host": self.ssh_host.get(), "port": self.ssh_port.get(), "user": self.ssh_user.get(),
            "password": self.ssh_pass.get(), "path": self.cfg_path.get(),
            "bed_x": self.bed_x.get(), "bed_y": self.bed_y.get(),
            "pitch": self.screw_pitch.get(), "grid_x": self.entry_x.get(), "grid_y": self.entry_y.get()
        }
        with open(SETTINGS_FILE, "w") as f: json.dump(data, f, indent=4)
        if not silent: messagebox.showinfo("Успех", "Настройки сохранены!")

    def fetch_ssh(self):
        try:
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            client.connect(hostname=self.ssh_host.get(), port=int(self.ssh_port.get()), 
                           username=self.ssh_user.get(), password=self.ssh_pass.get(), timeout=10)
            sftp = client.open_sftp()
            with sftp.open(self.cfg_path.get(), 'r') as f: content = f.read().decode('utf-8')
            sftp.close(); client.close()
            self.text_area.delete("1.0", tk.END); self.text_area.insert(tk.END, content)
            self.save_settings(silent=True)
            # Авто-парсинг JSON
            try:
                js = json.loads(content).get("bed_mesh default", {})
                if js:
                    self.entry_x.delete(0, tk.END); self.entry_x.insert(0, js.get("x_count", "5"))
                    self.entry_y.delete(0, tk.END); self.entry_y.insert(0, js.get("y_count", "5"))
            except: pass
            messagebox.showinfo("Успех", "Данные получены!")
        except Exception as e: messagebox.showerror("Ошибка SSH", str(e))

    def visualize(self, mode):
        text = self.text_area.get("1.0", tk.END).strip()
        nums = [float(n) for n in re.findall(r"[-+]?\d*\.\d+|\d+", text)]
        if not nums: return
        gx, gy = int(self.entry_x.get()), int(self.entry_y.get())
        if len(nums) < gx * gy: return
        matrix = np.array(nums[-(gx*gy):]).reshape((gy, gx))
        self.save_settings(silent=True)

        plt.close('all')
        if mode == "3d":
            fig = plt.figure("3D View", figsize=(10, 8))
            ax = fig.add_subplot(111, projection='3d')
            y, x = np.indices(matrix.shape)
            surf = ax.plot_surface(x, y, matrix, cmap='RdYlBu_r', edgecolor='black', alpha=0.8)
            fig.colorbar(surf, shrink=0.5, aspect=10)
        else:
            fig, ax = plt.subplots(figsize=(10, 10))
            bx, by = float(self.bed_x.get()), float(self.bed_y.get())
            im = ax.imshow(matrix, extent=[0, bx, 0, by], cmap='RdYlBu_r', origin='lower')
            # Текст с обводкой
            tx = np.linspace(bx/(gx*2), bx - bx/(gx*2), gx)
            ty = np.linspace(by/(gy*2), by - by/(gy*2), gy)
            for i in range(gy):
                for j in range(gx):
                    val = matrix[i, j]
                    t = ax.text(tx[j], ty[i], f"{val:.3f}", ha="center", va="center", fontweight='bold')
                    t.set_path_effects([path_effects.withStroke(linewidth=2, foreground="white")])
            
            # Расчет винтов
            corners = {"ПЛ": matrix[0,0], "ПП": matrix[0,-1], "ЗЛ": matrix[-1,0], "ЗП": matrix[-1,-1]}
            base = min(corners.values())
            pitch = float(self.screw_pitch.get())
            info_text = "Коррекция винтов (отн. низшей точки):\n"
            for k, v in corners.items():
                diff = v - base
                turns = diff / pitch
                info_text += f"{k}: {diff:+.3f}мм ({turns:.2f} об. {'ВНИЗ' if diff > 0 else 'ОК'})\n"
            plt.gcf().text(0.02, 0.02, info_text, fontsize=10, bbox=dict(facecolor='white', alpha=0.8))
            fig.colorbar(im)
        plt.show()

if __name__ == "__main__":
    root = tk.Tk(); app = TableVisualizer(root); root.mainloop()