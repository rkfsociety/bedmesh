import tkinter as tk
from tkinter import scrolledtext, messagebox, ttk
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
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
VERSION = "5.9"
REPO = "rkfsociety/bedmesh"
SETTINGS_FILE = "settings.json"

class BedMeshVisualizerWin:
    def __init__(self, root):
        self.root = root
        self.root.title(f"Bed Mesh Visualizer Pro v{VERSION}")
        self.root.geometry("1250x900")

        # КРИТИЧЕСКИЙ ФИКС: Обработка закрытия окна
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

        self.matrix = None
        self.current_theme = "dark"
        self.cleanup_old_files()
        self.settings = self.load_settings()

        self.themes = {
            "dark": {"bg": "#1e1e1e", "fg": "#d4d4d4", "head": "#252526", "text_bg": "#1e1e1e", "accent": "#007acc", "border": "#3c3c3c"},
            "light": {"bg": "#ffffff", "fg": "#333333", "head": "#f3f3f3", "text_bg": "#ffffff", "accent": "#007acc", "border": "#cccccc"}
        }

        self.style = ttk.Style()
        self.style.theme_use('default')

        # --- ИНТЕРФЕЙС ---
        self.header = tk.Frame(root, pady=10, padx=15); self.header.pack(fill="x")
        self.ssh_box = tk.LabelFrame(self.header, text=" ПАРАМЕТРЫ ПОДКЛЮЧЕНИЯ ", font=("Segoe UI", 9, "bold"), padx=10, pady=10)
        self.ssh_box.pack(side="left", fill="x", expand=True)

        row1 = tk.Frame(self.ssh_box); row1.pack(fill="x")
        self.ssh_host = self.create_input(row1, "IP:", "host", "192.168.1.100", 0, width=20)
        self.ssh_port = self.create_input(row1, "PORT:", "port", "22", 2, width=6)
        self.ssh_user = self.create_input(row1, "USER:", "user", "pi", 4, width=10)
        self.ssh_pass = self.create_input(row1, "PASS:", "password", "raspberry", 6, width=10, show="*")

        row2 = tk.Frame(self.ssh_box); row2.pack(fill="x", pady=(10, 0))
        self.cfg_path = tk.Entry(row2, font=("Segoe UI", 9)); self.cfg_path.insert(0, self.settings.get("path", "...cfg"))
        self.cfg_path.pack(side="left", fill="x", expand=True, padx=(0, 10))
        tk.Button(row2, text="ВЫТЯНУТЬ", command=self.fetch_ssh, bg="#007acc", fg="white", font=("Segoe UI", 9, "bold"), relief="flat", padx=15).pack(side="right")

        tk.Button(self.header, text="🌓", command=self.toggle_theme, width=4).pack(side="right", padx=(15, 0))

        # Метрики
        self.m_strip = tk.Frame(root, height=40); self.m_strip.pack(fill="x", padx=15, pady=5)
        self.lbl_var = tk.Label(self.m_strip, text="VARIANCE: ---", font=("Segoe UI", 12, "bold")); self.lbl_var.pack(side="left", padx=20)
        self.lbl_max = tk.Label(self.m_strip, text="MAX Z: ---"); self.lbl_max.pack(side="left", padx=20)
        self.lbl_min = tk.Label(self.m_strip, text="MIN Z: ---"); self.lbl_min.pack(side="left", padx=20)

        # Центр
        self.container = tk.Frame(root, padx=15, pady=5); self.container.pack(fill="both", expand=True)
        self.tabs = ttk.Notebook(self.container); self.tabs.pack(side="left", fill="both", expand=True)

        self.tab_data = tk.Frame(self.tabs); self.tabs.add(self.tab_data, text=" ДАННЫЕ ")
        self.tab_2d = tk.Frame(self.tabs); self.tabs.add(self.tab_2d, text=" 2D КАРТА ")
        self.tab_3d = tk.Frame(self.tabs); self.tabs.add(self.tab_3d, text=" 3D МОДЕЛЬ ")
        self.tab_stg = tk.Frame(self.tabs); self.tabs.add(self.tab_stg, text=" НАСТРОЙКИ ")

        self.text_editor = scrolledtext.ScrolledText(self.tab_data, font=("Consolas", 10), relief="flat", padx=10, pady=10)
        self.text_editor.pack(fill="both", expand=True)

        self.init_settings_tab()

        # Рекомендации
        self.rec_box = tk.LabelFrame(self.container, text=" ИНСТРУКЦИИ ", font=("Segoe UI", 9, "bold"), padx=10, pady=10, width=320)
        self.rec_box.pack(side="right", fill="both", padx=(15, 0))
        self.rec_box.pack_propagate(False)

        tk.Label(self.rec_box, text="СИСТЕМА:").pack(anchor="w")
        self.z_type = ttk.Combobox(self.rec_box, values=["Винты (углы)", "2 вала (Л/П)", "3 вала (Tri-Z)", "4 вала (Quad-Z)"], state="readonly")
        self.z_type.set(self.settings.get("z_sys", "Винты (углы)")); self.z_type.pack(fill="x", pady=5)
        self.z_type.bind("<<ComboboxSelected>>", lambda e: self.process_data())

        tk.Label(self.rec_box, text="ШАГ:").pack(anchor="w")
        self.z_pitch = ttk.Combobox(self.rec_box, values=["0.7", "0.5", "0.8"], state="readonly")
        self.z_pitch.set(self.settings.get("pitch", "0.7")); self.z_pitch.pack(fill="x", pady=5)
        self.z_pitch.bind("<<ComboboxSelected>>", lambda e: self.process_data())

        self.instr_label = tk.Label(self.rec_box, text="Ожидание данных...", justify="left", font=("Segoe UI", 9))
        self.instr_label.pack(fill="both", expand=True)

        tk.Button(root, text="⚡ ВИЗУАЛИЗИРОВАТЬ", command=self.process_data, bg="#28a745", fg="white", font=("Segoe UI", 11, "bold"), relief="flat", pady=10).pack(fill="x", padx=15, pady=10)

        self.apply_theme()
        
        # Обновления (daemon поток не мешает закрытию)
        threading.Thread(target=self.check_updates, daemon=True).start()

    def on_closing(self):
        """Принудительно завершает всё при закрытии окна"""
        plt.close('all')
        self.root.destroy()
        sys.exit(0)

    def create_input(self, master, label, key, default, col, width=10, show=None):
        tk.Label(master, text=label, font=("Segoe UI", 8)).grid(row=0, column=col, padx=(5, 2))
        e = tk.Entry(master, width=width, font=("Segoe UI", 9), show=show, relief="flat", highlightthickness=1)
        e.insert(0, self.settings.get(key, default)); e.grid(row=0, column=col+1); return e

    def init_settings_tab(self):
        self.stg_entries = {}
        cont = tk.Frame(self.tab_stg, padx=20, pady=20); cont.pack(fill="both")
        for i, (l, k, d) in enumerate([("Размер X", "bed_x", "250"), ("Размер Y", "bed_y", "250"), ("Точек X", "grid_x", "5"), ("Точек Y", "grid_y", "5")]):
            tk.Label(cont, text=l).grid(row=i, column=0, pady=5, sticky="w")
            e = tk.Entry(cont, width=10, relief="flat", highlightthickness=1); e.insert(0, self.settings.get(k, d)); e.grid(row=i, column=1, padx=10)
            self.stg_entries[k] = e
        tk.Button(cont, text="СОХРАНИТЬ", command=self.save_settings, bg="#007acc", fg="white", relief="flat").grid(row=4, column=0, columnspan=2, pady=20)

    def fetch_ssh(self):
        try:
            client = paramiko.SSHClient(); client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            client.connect(self.ssh_host.get(), int(self.ssh_port.get()), self.ssh_user.get(), self.ssh_pass.get(), timeout=10)
            sftp = client.open_sftp()
            with sftp.open(self.cfg_path.get(), 'r') as f: content = f.read().decode('utf-8')
            sftp.close(); client.close()
            self.text_editor.delete("1.0", tk.END); self.text_editor.insert(tk.END, content)
            self.tabs.select(self.tab_data)
        except Exception as e: messagebox.showerror("SSH Error", str(e))

    def process_data(self):
        raw = self.text_editor.get("1.0", tk.END).strip()
        if not raw: return
        match = re.search(r'"points":\s*"([\s\S]+?)"', raw)
        pts_content = match.group(1) if match else raw
        nums = [float(n) for n in re.findall(r"[-+]?\d*\.\d+|\d+", pts_content)]
        gx, gy = int(self.stg_entries["grid_x"].get()), int(self.stg_entries["grid_y"].get())
        if len(nums) < gx * gy: return
        self.matrix = np.array(nums[:gx*gy]).reshape((gy, gx))
        for i in range(len(self.matrix)):
            if i % 2 != 0: self.matrix[i] = self.matrix[i][::-1]
        
        v = np.max(self.matrix) - np.min(self.matrix)
        self.lbl_var.config(text=f"VARIANCE: {v:.3f} mm", fg="#f44336" if v > 0.2 else "#28a745")
        self.lbl_max.config(text=f"MAX Z: {np.max(self.matrix):.3f} mm")
        self.lbl_min.config(text=f"MIN Z: {np.min(self.matrix):.3f} mm")
        self.render_tab(self.tab_2d, "2d"); self.render_tab(self.tab_3d, "3d"); self.update_instructions()

    def render_tab(self, tab, mode):
        for w in tab.winfo_children(): w.destroy()
        is_dark = self.current_theme == "dark"
        plt.style.use('dark_background' if is_dark else 'default')
        fig = plt.figure(figsize=(6, 6), dpi=100); fig.patch.set_facecolor(self.themes[self.current_theme]["bg"])
        bx, by = float(self.stg_entries["bed_x"].get()), float(self.stg_entries["bed_y"].get())
        gx, gy = int(self.stg_entries["grid_x"].get()), int(self.stg_entries["grid_y"].get())

        if mode == "3d":
            ax = fig.add_subplot(111, projection='3d'); ax.set_facecolor(self.themes[self.current_theme]["bg"])
            X, Y = np.meshgrid(np.linspace(0, bx, gx), np.linspace(0, by, gy))
            ax.plot_surface(X, Y, self.matrix, cmap='RdYlBu_r', edgecolor='#444444', alpha=0.8)
        else:
            ax = fig.add_subplot(111)
            xe, ye = np.linspace(0, bx, gx + 1), np.linspace(0, by, gy + 1)
            ax.pcolormesh(xe, ye, self.matrix, cmap='RdYlBu_r', edgecolors='black', linewidth=0.5)
            xc, yc = (xe[:-1] + xe[1:]) / 2, (ye[:-1] + ye[1:]) / 2
            for i in range(gy):
                for j in range(gx):
                    t = ax.text(xc[j], yc[i], f"{self.matrix[i,j]:.3f}", ha="center", va="center", fontweight='bold', fontsize=9, color="black" if not is_dark else "white")
                    t.set_path_effects([path_effects.withStroke(linewidth=2, foreground="white" if not is_dark else "black")])
            ax.set_aspect('equal')
        FigureCanvasTkAgg(fig, master=tab).get_tk_widget().pack(fill="both", expand=True)

    def update_instructions(self):
        z_sys, p = self.z_type.get(), float(self.z_pitch.get())
        pts = {}
        if "Винты" in z_sys: pts = {"ПЛ": self.matrix[0,0], "ПП": self.matrix[0,-1], "ЗЛ": self.matrix[-1,0], "ЗП": self.matrix[-1,-1]}
        elif "2 вала" in z_sys: pts = {"Левый": np.mean(self.matrix[:, 0]), "Правый": np.mean(self.matrix[:, -1])}
        elif "3 вала" in z_sys: pts = {"П.Лево": self.matrix[0,0], "П.Право": self.matrix[0,-1], "З.Центр": self.matrix[-1, int(self.stg_entries["grid_x"].get())//2]}
        elif "4 вала" in z_sys: pts = {"ПЛ": self.matrix[0,0], "ПП": self.matrix[0,-1], "ЗЛ": self.matrix[-1,0], "ЗП": self.matrix[-1,-1]}
        low = min(pts.values()); res = ""
        for name, val in pts.items():
            diff = val - low; dir_s = "🔽 ВНИЗ" if diff > 0 else "✅ OK" if diff == 0 else "🔼 ВВЕРХ"
            res += f"● {name}:\n  {diff:+.3f} мм | {abs(diff/p):.2f} об. [{dir_s}]\n\n"
        self.instr_label.config(text=res)

    def apply_theme(self):
        t = self.themes[self.current_theme]; self.root.config(bg=t["bg"])
        self.style.configure("TNotebook", background=t["bg"], borderwidth=0)
        self.style.configure("TNotebook.Tab", background=t["head"], foreground=t["fg"], padding=[10, 5]); self.style.map("TNotebook.Tab", background=[("selected", t["accent"])], foreground=[("selected", "white")])
        def paint(parent):
            for w in parent.winfo_children():
                try:
                    if isinstance(w, (tk.Frame, tk.LabelFrame, tk.Label)): w.config(bg=t["bg"], fg=t["fg"])
                    elif isinstance(w, (tk.Entry, scrolledtext.ScrolledText)): w.config(bg=t["text_bg"], fg=t["fg"], insertbackground=t["fg"])
                except: pass
                paint(w)
        paint(self.root); self.header.config(bg=t["head"]); self.ssh_box.config(bg=t["head"])

    def toggle_theme(self):
        self.current_theme = "light" if self.current_theme == "dark" else "dark"; self.apply_theme()
        if self.matrix is not None: self.process_data()

    def check_updates(self):
        try:
            r = requests.get(f"https://api.github.com/repos/{REPO}/releases/latest", timeout=5)
            latest = r.json().get("tag_name", "").replace("v", "")
            if latest > VERSION: self.lbl_var.config(text=f"UPDATE v{latest}!", fg="#007acc")
        except: pass

    def save_settings(self):
        d = {k: e.get() for k, e in self.stg_entries.items()}
        d.update({"host": self.ssh_host.get(), "port": self.ssh_port.get(), "user": self.ssh_user.get(), "password": self.ssh_pass.get(), "path": self.cfg_path.get(), "z_sys": self.z_type.get(), "pitch": self.z_pitch.get()})
        with open(SETTINGS_FILE, "w") as f: json.dump(d, f, indent=4)
        messagebox.showinfo("OK", "Настройки сохранены")

    def load_settings(self):
        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE, "r") as f: return json.load(f)
            except: return {}
        return {}

    def cleanup_old_files(self):
        for f in ["updater.bat", "Bed_Mesh_Viz_new.exe"]:
            if os.path.exists(f): os.remove(f)

if __name__ == "__main__":
    root = tk.Tk(); app = BedMeshVisualizerWin(root); root.mainloop()