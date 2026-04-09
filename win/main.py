import customtkinter as ctk
import logic, styles
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.patheffects as path_effects
import numpy as np
from tkinter import messagebox
import threading, sys

ctk.set_appearance_mode("dark")

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title(f"Bed Mesh Visualizer Win v{logic.VERSION}")
        self.geometry("1300x900")
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        self.matrix = None
        self.settings = logic.load_settings()
        logic.cleanup_old_files()

        # Интерфейс (Колонки)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # --- Sidebar (SSH + Settings) ---
        self.sidebar = ctk.CTkFrame(self, width=320, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        
        ctk.CTkLabel(self.sidebar, text="SETTINGS & SSH", font=styles.FONT_BOLD).pack(pady=20)
        
        self.ip = self.create_in("IP Address", "host", "192.168.1.100")
        self.port = self.create_in("Port", "port", "22")
        self.user = self.create_in("User", "user", "pi")
        self.pwd = self.create_in("Password", "password", "raspberry", show="*")
        self.path = self.create_in("Config Path", "path", "/home/pi/printer_data/config/printer_mutable.cfg")
        
        ctk.CTkButton(self.sidebar, text="FETCH DATA", fg_color=styles.THEME["dark"]["accent"], command=self.fetch).pack(pady=10, padx=20)
        
        ctk.CTkLabel(self.sidebar, text="BED GEOMETRY").pack(pady=(20,0))
        self.bx = self.create_in("Bed X", "bed_x", "250")
        self.by = self.create_in("Bed Y", "bed_y", "250")
        self.gx = self.create_in("Grid X", "grid_x", "5")
        self.gy = self.create_in("Grid Y", "grid_y", "5")

        # --- Main Area ---
        self.main_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.main_frame.grid(row=0, column=1, padx=20, pady=20, sticky="nsew")
        
        self.tabs = ctk.CTkTabview(self.main_frame)
        self.tabs.pack(fill="both", expand=True)
        self.tab_2d = self.tabs.add("2D HEATMAP")
        self.tab_3d = self.tabs.add("3D MODEL")
        self.tab_raw = self.tabs.add("RAW DATA")
        
        self.text_editor = ctk.CTkTextbox(self.tab_raw, font=("Consolas", 12))
        self.text_editor.pack(fill="both", expand=True)

        # --- Right Panel (Instructions) ---
        self.right_p = ctk.CTkFrame(self, width=280)
        self.right_p.grid(row=0, column=2, padx=(0,20), pady=20, sticky="nsew")
        
        ctk.CTkLabel(self.right_p, text="INSTRUCTIONS", font=styles.FONT_BOLD).pack(pady=10)
        self.z_sys = ctk.CTkOptionMenu(self.right_p, values=["Винты (углы)", "2 вала (Л/П)", "3 вала (Tri-Z)", "4 вала (Quad-Z)"])
        self.z_sys.set(self.settings.get("z_sys", "Винты (углы)"))
        self.z_sys.pack(pady=10, padx=10)
        
        self.pitch = ctk.CTkOptionMenu(self.right_p, values=["0.7", "0.5", "0.8"])
        self.pitch.set(self.settings.get("pitch", "0.7"))
        self.pitch.pack(pady=10, padx=10)

        self.instr_label = ctk.CTkLabel(self.right_p, text="Waiting for data...", justify="left", font=styles.FONT_UI)
        self.instr_label.pack(fill="both", expand=True, padx=10)

        # Bottom Button
        self.btn_run = ctk.CTkButton(self, text="⚡ VISUALIZE & ANALYZE", height=50, fg_color=styles.THEME["dark"]["success"], 
                                    font=styles.FONT_BOLD, command=self.run_analysis)
        self.btn_run.grid(row=1, column=0, columnspan=3, padx=20, pady=10, sticky="ew")

        # Background Update Check
        threading.Thread(target=self.check_upd, daemon=True).start()

    def create_in(self, placeholder, key, default, show=None):
        e = ctk.CTkEntry(self.sidebar, placeholder_text=placeholder, show=show)
        e.insert(0, self.settings.get(key, default))
        e.pack(pady=5, padx=20, fill="x")
        return e

    def fetch(self):
        try:
            content = logic.fetch_ssh(self.ip.get(), self.port.get(), self.user.get(), self.pwd.get(), self.path.get())
            self.text_editor.delete("0.0", "end")
            self.text_editor.insert("end", content)
            self.tabs.set("RAW DATA")
        except Exception as e: messagebox.showerror("SSH Error", str(e))

    def run_analysis(self):
        raw = self.text_editor.get("0.0", "end").strip()
        gx, gy = int(self.gx.get()), int(self.gy.get())
        matrix, err = logic.parse_data(raw, gx, gy)
        
        if matrix is not None:
            self.matrix = matrix
            self.update_rec()
            self.draw_plots()
            # Save current settings
            logic.save_settings({
                "host": self.ip.get(), "port": self.port.get(), "user": self.user.get(), 
                "password": self.pwd.get(), "path": self.path.get(), "bed_x": self.bx.get(), 
                "bed_y": self.by.get(), "grid_x": self.gx.get(), "grid_y": self.gy.get(),
                "z_sys": self.z_sys.get(), "pitch": self.pitch.get()
            })
        else: messagebox.showwarning("Data Error", err)

    def update_rec(self):
        recs = logic.get_recommendations(self.matrix, self.z_sys.get(), float(self.pitch.get()), int(self.gx.get()))
        text = ""
        for r in recs:
            text += f"● {r['name']}:\n  {r['mm']:+.3f}mm | {r['turns']:.2f}об.\n  [{r['dir']}]\n\n"
        self.instr_label.configure(text=text)

    def draw_plots(self):
        for tab, mode in [(self.tab_2d, "2d"), (self.tab_3d, "3d")]:
            for w in tab.winfo_children(): w.destroy()
            plt.style.use('dark_background')
            fig = plt.figure(figsize=(5, 5), dpi=100)
            fig.patch.set_facecolor("#2b2b2b")
            bx, by = float(self.bx.get()), float(self.by.get())
            gx, gy = int(self.gx.get()), int(self.gy.get())

            if mode == "3d":
                ax = fig.add_subplot(111, projection='3d')
                ax.set_facecolor("#2b2b2b")
                X, Y = np.meshgrid(np.linspace(0, bx, gx), np.linspace(0, by, gy))
                ax.plot_surface(X, Y, self.matrix, cmap='RdYlBu_r', edgecolor='#444444', alpha=0.8)
            else:
                ax = fig.add_subplot(111)
                xe, ye = np.linspace(0, bx, gx + 1), np.linspace(0, by, gy + 1)
                ax.pcolormesh(xe, ye, self.matrix, cmap='RdYlBu_r', edgecolors='black', linewidth=0.5)
                xc, yc = (xe[:-1] + xe[1:]) / 2, (ye[:-1] + ye[1:]) / 2
                for i in range(gy):
                    for j in range(gx):
                        t = ax.text(xc[j], yc[i], f"{self.matrix[i,j]:.3f}", ha="center", va="center", fontweight='bold', color="white", fontsize=8)
                        t.set_path_effects([path_effects.withStroke(linewidth=2, foreground="black")])
                ax.set_aspect('equal')
            
            FigureCanvasTkAgg(fig, master=tab).get_tk_widget().pack(fill="both", expand=True)

    def check_upd(self):
        new_v = logic.check_updates()
        if new_v: self.btn_run.configure(text=f"⚡ UPDATE AVAILABLE v{new_v}! CLICK TO ANALYZE")

    def on_closing(self):
        plt.close('all')
        self.destroy()
        sys.exit(0)

if __name__ == "__main__":
    app = App()
    app.mainloop()