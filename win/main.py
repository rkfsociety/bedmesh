import customtkinter as ctk
import logic, styles, ui_elements
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.patheffects as path_effects
import numpy as np
import sys, threading
from tkinter import messagebox

ctk.set_appearance_mode("dark")

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title(f"Bed Mesh Visualizer Win v{logic.VERSION}")
        self.geometry("1350x900")
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        self.matrix = None
        self.settings = logic.load_settings()

        # Layout
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # --- SIDEBAR ---
        self.sidebar = ctk.CTkFrame(self, width=300, corner_radius=0)
        self.sidebar.grid(row=0, column=0, rowspan=2, sticky="nsew")
        
        ctk.CTkLabel(self.sidebar, text="SSH & CONFIG", font=styles.FONTS["title"]).pack(pady=(20, 10))
        
        self.ip = ui_elements.LabeledEntry(self.sidebar, "IP ADDRESS", self.settings.get("host", "192.168.1.100"))
        self.port = ui_elements.LabeledEntry(self.sidebar, "PORT", self.settings.get("port", "22"))
        self.user = ui_elements.LabeledEntry(self.sidebar, "USER", self.settings.get("user", "pi"))
        self.pwd = ui_elements.LabeledEntry(self.sidebar, "PASSWORD", self.settings.get("password", "raspberry"), show="*")
        self.path = ui_elements.LabeledEntry(self.sidebar, "CONFIG PATH", self.settings.get("path", "/home/pi/printer_data/config/printer_mutable.cfg"))
        
        ctk.CTkButton(self.sidebar, text="FETCH FROM PRINTER", command=self.fetch).pack(pady=10, padx=20)
        
        ctk.CTkLabel(self.sidebar, text="BED GEOMETRY", font=styles.FONTS["ui_bold"]).pack(pady=(20, 5))
        self.bx = ui_elements.LabeledEntry(self.sidebar, "BED X (mm)", self.settings.get("bed_x", "250"))
        self.by = ui_elements.LabeledEntry(self.sidebar, "BED Y (mm)", self.settings.get("bed_y", "250"))
        self.gx = ui_elements.LabeledEntry(self.sidebar, "GRID X (pts)", self.settings.get("grid_x", "5"))
        self.gy = ui_elements.LabeledEntry(self.sidebar, "GRID Y (pts)", self.settings.get("grid_y", "5"))

        # --- MAIN VIEW ---
        self.main_area = ctk.CTkFrame(self, fg_color="transparent")
        self.main_area.grid(row=0, column=1, padx=20, pady=20, sticky="nsew")
        
        self.tabs = ctk.CTkTabview(self.main_area)
        self.tabs.pack(fill="both", expand=True)
        self.t2d = self.tabs.add("2D HEATMAP")
        self.t3d = self.tabs.add("3D MODEL")
        self.traw = self.tabs.add("RAW DATA")
        
        self.text_editor = ctk.CTkTextbox(self.traw, font=styles.FONTS["code"])
        self.text_editor.pack(fill="both", expand=True)

        # --- RIGHT PANEL ---
        self.right = ctk.CTkFrame(self, width=320)
        self.right.grid(row=0, column=2, padx=(0, 20), pady=20, sticky="nsew")
        self.right.pack_propagate(False)

        ctk.CTkLabel(self.right, text="ALIGNMENT GUIDE", font=styles.FONTS["ui_bold"]).pack(pady=15)
        
        self.z_menu = ctk.CTkOptionMenu(self.right, 
                                        values=["Винты (углы)", "2 вала (Л/П)", "3 вала (Tri-Z)", "4 вала (Quad-Z)"],
                                        command=self.refresh_recs)
        self.z_menu.set(self.settings.get("z_sys", "Винты (углы)"))
        self.z_menu.pack(pady=10, padx=20, fill="x")

        self.p_label = ctk.CTkLabel(self.right, text="SCREW PITCH:")
        self.p_label.pack(pady=(10, 0))
        self.p_menu = ctk.CTkOptionMenu(self.right, values=["0.7", "0.5", "0.8"], command=self.refresh_recs)
        self.p_menu.set(self.settings.get("pitch", "0.7"))
        self.p_menu.pack(pady=5, padx=20, fill="x")

        self.instr = ctk.CTkLabel(self.right, text="Waiting for data...", justify="left", font=styles.FONTS["ui"])
        self.instr.pack(pady=30, padx=15, fill="both")

        # --- RUN BUTTON ---
        self.btn = ctk.CTkButton(self, text="⚡ VISUALIZE & ANALYZE", height=60, 
                                 fg_color=styles.COLORS["dark"]["success"], 
                                 font=styles.FONTS["title"], command=self.run)
        self.btn.grid(row=1, column=1, columnspan=2, padx=20, pady=(0, 20), sticky="ew")

    def fetch(self):
        try:
            content = logic.fetch_ssh(self.ip.get(), self.port.get(), self.user.get(), self.pwd.get(), self.path.get())
            self.text_editor.delete("0.0", "end")
            self.text_editor.insert("end", content)
            self.tabs.set("RAW DATA")
        except Exception as e:
            messagebox.showerror("SSH Error", str(e))

    def refresh_recs(self, _=None):
        if self.matrix is not None:
            txt, is_screws = logic.get_recs(self.matrix, self.z_menu.get(), float(self.p_menu.get()), int(self.gx.get()))
            self.instr.configure(text=txt)
            if is_screws:
                self.p_label.pack(); self.p_menu.pack(pady=5, padx=20, fill="x")
            else:
                self.p_label.pack_forget(); self.p_menu.pack_forget()

    def run(self):
        raw = self.text_editor.get("0.0", "end").strip()
        gx, gy = int(self.gx.get()), int(self.gy.get())
        self.matrix, err = logic.parse_points(raw, gx, gy)
        
        if self.matrix is not None:
            self.refresh_recs()
            self.draw()
            # Save settings
            logic.save_settings({
                "host": self.ip.get(), "port": self.port.get(), "user": self.user.get(),
                "password": self.pwd.get(), "path": self.path.get(),
                "bed_x": self.bx.get(), "bed_y": self.by.get(),
                "grid_x": self.gx.get(), "grid_y": self.gy.get(),
                "z_sys": self.z_menu.get(), "pitch": self.p_menu.get()
            })
        else:
            messagebox.showwarning("Data Error", err)

    def draw(self):
        # Отрисовка вкладок 2D и 3D
        for tab, mode in [(self.t2d, "2d"), (self.t3d, "3d")]:
            for w in tab.winfo_children(): w.destroy()
            
            plt.style.use('dark_background')
            fig = plt.figure(figsize=(6, 6), dpi=100)
            fig.patch.set_facecolor("#1a1a1a") # Синхронизация с фоном табов
            
            bx, by = float(self.bx.get()), float(self.by.get())
            gx, gy = int(self.gx.get()), int(self.gy.get())

            if mode == "3d":
                ax = fig.add_subplot(111, projection='3d')
                ax.set_facecolor("#1a1a1a")
                X, Y = np.meshgrid(np.linspace(0, bx, gx), np.linspace(0, by, gy))
                ax.plot_surface(X, Y, self.matrix, cmap='RdYlBu_r', edgecolor='#444444', alpha=0.8)
                ax.set_xlabel('X')
                ax.set_ylabel('Y')
            else:
                ax = fig.add_subplot(111)
                xe, ye = np.linspace(0, bx, gx + 1), np.linspace(0, by, gy + 1)
                im = ax.pcolormesh(xe, ye, self.matrix, cmap='RdYlBu_r', edgecolors='black', linewidth=0.5)
                xc, yc = (xe[:-1] + xe[1:]) / 2, (ye[:-1] + ye[1:]) / 2
                for i in range(gy):
                    for j in range(gx):
                        t = ax.text(xc[j], yc[i], f"{self.matrix[i,j]:.3f}", ha="center", va="center", fontweight='bold', color="white", fontsize=8)
                        t.set_path_effects([path_effects.withStroke(linewidth=2, foreground="black")])
                ax.set_aspect('equal')
            
            canvas = FigureCanvasTkAgg(fig, master=tab)
            canvas.draw()
            canvas.get_tk_widget().pack(fill="both", expand=True)

    def on_closing(self):
        plt.close('all')
        self.destroy()
        sys.exit(0)

if __name__ == "__main__":
    App().mainloop()