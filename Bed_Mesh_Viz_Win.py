import tkinter as tk
from tkinter import scrolledtext, messagebox, ttk
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
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
VERSION = "5.5"
REPO = "rkfsociety/bedmesh"
SETTINGS_FILE = "settings.json"

class BedMeshVisualizerWin:
    def __init__(self, root):
        self.root = root
        self.root.title(f"Bed Mesh Visualizer Pro v{VERSION}")
        self.root.geometry("1200x850")

        self.matrix = None
        self.current_theme = "light"
        self.cleanup_old_files()
        self.settings = self.load_settings()

        # Настройка цветов тем
        self.colors = {
            "light": {"bg": "#f0f0f0", "fg": "#000000", "text_bg": "#ffffff", "frame_bg": "#e1e1e1", "accent": "#2196F3"},
            "dark": {"bg": "#2d2d2d", "fg": "#ffffff", "text_bg": "#1e1e1e", "frame_bg": "#3d3d3d", "accent": "#1976D2"}
        }

        # --- ВЕРХНЯЯ ПАНЕЛЬ (SSH + ТЕМА) ---
        self.top_frame = tk.Frame(root, padx=10, pady=5)
        self.top_frame.pack(fill="x")

        self.ssh_frame = tk.LabelFrame(self.top_frame, text=" SSH Подключение ", padx=5, pady=5)
        self.ssh_frame.pack(side="left", fill="x", expand=True)

        self.ssh_host = self.add_ssh_entry(self.ssh_frame, "IP:", self.settings.get("host", "192.168.1.100"), 0, 1)
        self.ssh_port = self.add_ssh_entry(self.ssh_frame, "Порт:", self.settings.get("port", "22"), 0, 3)
        self.ssh_user = self.add_ssh_entry(self.ssh_frame, "User:", self.settings.get("user", "pi"), 0, 5)
        self.ssh_pass = self.add_ssh_entry(self.ssh_frame, "Pass:", self.settings.get("password", "raspberry"), 0, 7, show="*")
        
        self.cfg_path = tk.Entry(self.ssh_frame, width=50); self.cfg_path.insert(0, self.settings.get("path", "...cfg"))
        self.cfg_path.grid(row=1, column=0, columnspan=6, padx=5, pady=5, sticky="w")
        
        tk.Button(self.ssh_frame, text="ВЫТЯНУТЬ", command=self.fetch_ssh, bg="#2196F3", fg="white", font=("Arial", 8, "bold")).grid(row=1, column=6, columnspan=2, sticky="we")

        self.btn_theme = tk.Button(self.top_frame, text="🌓", command=self.toggle_theme, width=4)
        self.btn_theme.pack(side="right", padx=5)

        # --- ПАНЕЛЬ МЕТРИК ---
        self.mid_frame = tk.Frame(root, padx=10); self.mid_frame.pack(fill="x")
        self.metric_frame = tk.LabelFrame(self.mid_frame, text=" Анализ ", padx=10)
        self.metric_frame.pack(fill="x", pady=5)
        
        self.lbl_var = tk.Label(self.metric_frame, text="Variance: ---", font=("Arial", 11, "bold")); self.lbl_var.pack(side="left", padx=20)
        self.lbl_max = tk.Label(self.metric_frame, text="Max Z: ---"); self.lbl_max.pack(side="left", padx=20)
        self.lbl_min = tk.Label(self.metric_frame, text="Min Z: ---"); self.lbl_min.pack(side="left", padx=20)

        # --- ОСНОВНОЙ КОНТЕНТ (ВКЛАДКИ + РЕКОМЕНДАЦИИ) ---
        self.main_split = tk.Frame(root, padx=10); self.main_split.pack(fill="both", expand=True)

        # Левая часть: Вкладки
        self.notebook = ttk.Notebook(self.main_split)
        self.notebook.pack(side="left", fill="both", expand=True)

        self.tab_text = tk.Frame(self.notebook)
        self.tab_2d = tk.Frame(self.notebook)
        self.tab_3d = tk.Frame(self.notebook)
        self.tab_cfg = tk.Frame(self.notebook)

        self.notebook.add(self.tab_text, text=" Данные Mesh ")
        self.notebook.add(self.tab_2d, text=" 2D Карта ")
        self.notebook.add(self.tab_3d, text=" 3D Модель ")
        self.notebook.add(self.tab_cfg, text=" Настройки стола ")

        # Содержимое вкладок
        self.text_area = scrolledtext.ScrolledText(self.tab_text, font=("Consolas", 10))
        self.text_area.pack(fill="both", expand=True)

        self.setup_cfg_tab()

        # Правая часть: Рекомендации (Всегда виден)
        self.rec_frame = tk.LabelFrame(self.main_split, text=" Рекомендации по выравниванию ", padx=10, pady=10, width=300)
        self.rec_frame.pack(side="right", fill="both", padx=(10, 0))
        self.rec_frame.pack_propagate(False)

        tk.Label(self.rec_frame, text="Система:").pack(anchor="w")
        self.z_sys = ttk.Combobox(self.rec_frame, values=["Винты (углы)", "2 вала (Л/П)", "3 вала (Tri-Z)", "4 вала (Quad-Z)"], state="readonly")
        self.z_sys.set(self.settings.get("z_sys", "Винты (углы)")); self.z_sys.pack(fill="x", pady=5)
        self.z_sys.bind("<<ComboboxSelected>>", lambda e: self.update_viz())

        tk.Label(self.rec_frame, text="Шаг винта:").pack(anchor="w")
        self.pitch = ttk.Combobox(self.rec_frame, values=["0.7", "0.5", "0.8"], state="readonly")
        self.pitch.set(self.settings.get("pitch", "0.7")); self.pitch.pack(fill="x", pady=5)
        self.pitch.bind("<<ComboboxSelected>>", lambda e: self.update_viz())

        self.rec_display = tk.Label(self.rec_frame, text="\nЗагрузите данные...", justify="left", font=("Consolas", 10))
        self.rec_display.pack(pady=20, fill="both")

        # Кнопка действия
        self.btn_viz = tk.Button(root, text="🚀 ОБНОВИТЬ И ВИЗУАЛИЗИРОВАТЬ", command=self.update_viz, bg="#4CAF50", fg="white", font=("Arial", 10, "bold"), pady=10)
        self.btn_viz.pack(fill="x", padx=10, pady=10)

        self.apply_theme()

    def add_ssh_entry(self, master, label, default, r, c, show=None):
        tk.Label(master, text=label).grid(row=r, column=c-1, padx=2)
        e = tk.Entry(master, width=12, show=show); e.insert(0, default); e.grid(row=r, column=c, padx=2); return e

    def setup_cfg_tab(self):
        self.entries = {}
        frame = tk.Frame(self.tab_cfg, padx=20, pady=20)
        frame.pack(fill="both")
        fields = [("bed_x", "250"), ("bed_y", "250"), ("grid_x", "5"), ("grid_y", "5")]
        for i, (key, default) in enumerate(fields):
            tk.Label(frame, text=f"Параметр {key}:").grid(row=i, column=0, pady=5, sticky="w")
            e = tk.Entry(frame, width=10); e.insert(0, self.settings.get(key, default)); e.grid(row=i, column=1, padx=10)
            self.entries[key] = e
        tk.Button(frame, text="Сохранить настройки", command=self.save_settings).grid(row=4, column=0, columnspan=2, pady=20)

    def toggle_theme(self):
        self.current_theme = "dark" if self.current_theme == "light" else "light"
        self.apply_theme()
        if self.matrix is not None: self.update_viz()

    def apply_theme(self):
        theme = self.colors[self.current_theme]
        self.root.config(bg=theme["bg"])
        # Рекурсивная покраска виджетов
        def color_widgets(parent):
            for widget in parent.winfo_children():
                try:
                    if isinstance(widget, (tk.Frame, tk.LabelFrame, tk.Label)):
                        widget.config(bg=theme["bg"], fg=theme["fg"])
                    elif isinstance(widget, tk.Entry):
                        widget.config(bg=theme["text_bg"], fg=theme["fg"], insertbackground=theme["fg"])
                    elif isinstance(widget, scrolledtext.ScrolledText):
                        widget.config(bg=theme["text_bg"], fg=theme["fg"], insertbackground=theme["fg"])
                except: pass
                color_widgets(widget)
        color_widgets(self.root)
        self.rec_frame.config(bg=theme["bg"], fg=theme["fg"])

    def fetch_ssh(self):
        try:
            client = paramiko.SSHClient(); client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            client.connect(self.ssh_host.get(), int(self.ssh_port.get()), self.ssh_user.get(), self.ssh_pass.get(), timeout=10)
            sftp = client.open_sftp()
            with sftp.open(self.cfg_path.get(), 'r') as f: content = f.read().decode('utf-8')
            sftp.close(); client.close()
            self.text_area.delete("1.0", tk.END); self.text_area.insert(tk.END, content)
            self.notebook.select(self.tab_text)
        except Exception as e: messagebox.showerror("SSH Error", str(e))

    def update_viz(self):
        text = self.text_area.get("1.0", tk.END).strip()
        if not text: return
        try:
            nums = [float(n) for n in re.findall(r"[-+]?\d*\.\d+|\d+", text)]
            gx, gy = int(self.entries["grid_x"].get()), int(self.entries["grid_y"].get())
            if len(nums) < gx * gy: return
            self.matrix = np.array(nums[:gx*gy]).reshape((gy, gx))
            for i in range(len(self.matrix)):
                if i % 2 != 0: self.matrix[i] = self.matrix[i][::-1]
            
            # Обновление метрик
            v = np.max(self.matrix) - np.min(self.matrix)
            self.lbl_var.config(text=f"Variance: {v:.3f} мм")
            self.lbl_max.config(text=f"Max Z: {np.max(self.matrix):.3f} мм")
            self.lbl_min.config(text=f"Min Z: {np.min(self.matrix):.3f} мм")

            # Отрисовка 2D
            self.draw_plot(self.tab_2d, "2d")
            # Отрисовка 3D
            self.draw_plot(self.tab_3d, "3d")
            # Расчет рекомендаций
            self.calc_rec()
        except: pass

    def draw_plot(self, tab, mode):
        for widget in tab.winfo_children(): widget.destroy()
        
        # Настройка стиля под тему
        is_dark = self.current_theme == "dark"
        plt.style.use('dark_background' if is_dark else 'default')
        fig = plt.figure(figsize=(6, 6), dpi=100)
        fig.patch.set_facecolor(self.colors[self.current_theme]["bg"])
        
        bx, by = float(self.entries["bed_x"].get()), float(self.entries["bed_y"].get())
        gx, gy = int(self.entries["grid_x"].get()), int(self.entries["grid_y"].get())

        if mode == "3d":
            ax = fig.add_subplot(111, projection='3d')
            ax.set_facecolor(self.colors[self.current_theme]["bg"])
            X, Y = np.meshgrid(np.linspace(0, bx, gx), np.linspace(0, by, gy))
            ax.plot_surface(X, Y, self.matrix, cmap='RdYlBu_r', edgecolor='black' if not is_dark else '#444444')
        else:
            ax = fig.add_subplot(111)
            xe, ye = np.linspace(0, bx, gx + 1), np.linspace(0, by, gy + 1)
            im = ax.pcolormesh(xe, ye, self.matrix, cmap='RdYlBu_r', edgecolors='black')
            xc, yc = (xe[:-1] + xe[1:]) / 2, (ye[:-1] + ye[1:]) / 2
            for i in range(gy):
                for j in range(gx):
                    t = ax.text(xc[j], yc[i], f"{self.matrix[i,j]:.3f}", ha="center", va="center", fontweight='bold', color="black" if not is_dark else "white")
                    t.set_path_effects([path_effects.withStroke(linewidth=2, foreground="white" if not is_dark else "black")])
            ax.set_aspect('equal')

        canvas = FigureCanvasTkAgg(fig, master=tab)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)

    def calc_rec(self):
        z_type, p = self.z_sys.get(), float(self.pitch.get())
        pts = {}
        if z_type == "Винты (углы)":
            pts = {"ПЛ": self.matrix[0,0], "ПП": self.matrix[0,-1], "ЗЛ": self.matrix[-1,0], "ЗП": self.matrix[-1,-1]}
        elif z_type == "2 вала (Л/П)":
            pts = {"Левый вал": np.mean(self.matrix[:, 0]), "Правый вал": np.mean(self.matrix[:, -1])}
        elif z_type == "3 вала (Tri-Z)":
            pts = {"Перед Лево": self.matrix[0,0], "Перед Право": self.matrix[0,-1], "Зад Центр": self.matrix[-1, int(self.entries["grid_x"].get())//2]}
        elif z_type == "4 вала (Quad-Z)":
            pts = {"ПЛ": self.matrix[0,0], "ПП": self.matrix[0,-1], "ЗЛ": self.matrix[-1,0], "ЗП": self.matrix[-1,-1]}

        low = min(pts.values())
        res = ""
        for name, val in pts.items():
            diff = val - low
            res += f"{name}:\n {diff:+.3f} мм | {abs(diff/p):.2f} об.\n {'🔽 ВНИЗ' if diff>0 else '✅ ОПОРА' if diff==0 else '🔼 ВВЕРХ'}\n\n"
        self.rec_display.config(text=res, fg=self.colors[self.current_theme]["fg"])

    def cleanup_old_files(self):
        for f in ["updater.bat", "Bed_Mesh_Viz_new.exe"]:
            if os.path.exists(f): 
                try: os.remove(f)
                except: pass

    def load_settings(self):
        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE, "r") as f: return json.load(f)
            except: return {}
        return {}

    def save_settings(self):
        d = {k: e.get() for k, e in self.entries.items()}
        d.update({"host": self.ssh_host.get(), "port": self.ssh_port.get(), "user": self.ssh_user.get(), "password": self.ssh_pass.get(), "path": self.cfg_path.get(), "z_sys": self.z_sys.get(), "pitch": self.pitch.get()})
        with open(SETTINGS_FILE, "w") as f: json.dump(d, f, indent=4)
        messagebox.showinfo("OK", "Сохранено")

    def check_updates(self):
        try:
            r = requests.get(f"https://api.github.com/repos/{REPO}/releases/latest", timeout=5)
            latest = r.json().get("tag_name", "").replace("v", "")
            if latest > VERSION: self.update_status.config(text=f"Доступно v{latest}", fg="green")
        except: pass

if __name__ == "__main__":
    root = tk.Tk(); app = BedMeshVisualizerWin(root); root.mainloop()