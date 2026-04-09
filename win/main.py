import customtkinter as ctk
import logic, styles, ui_elements
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import numpy as np
import sys

ctk.set_appearance_mode("dark")

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title(f"Bed Mesh Visualizer Win v{logic.VERSION}")
        self.geometry("1300(x)900")
        self.matrix = None
        self.settings = logic.load_settings()

        # Layout
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Sidebar
        self.sidebar = ctk.CTkFrame(self, width=300, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.ip = ui_elements.LabeledEntry(self.sidebar, "IP Address", self.settings.get("host", "192.168.1.100"))
        self.port = ui_elements.LabeledEntry(self.sidebar, "Port", self.settings.get("port", "22"))
        self.user = ui_elements.LabeledEntry(self.sidebar, "User", self.settings.get("user", "pi"))
        self.pwd = ui_elements.LabeledEntry(self.sidebar, "Password", self.settings.get("password", "raspberry"), show="*")
        
        self.gx = ui_elements.LabeledEntry(self.sidebar, "Grid X", self.settings.get("grid_x", "5"))
        self.gy = ui_elements.LabeledEntry(self.sidebar, "Grid Y", self.settings.get("grid_y", "5"))

        # Main View
        self.tabs = ctk.CTkTabview(self)
        self.tabs.grid(row=0, column=1, padx=20, pady=20, sticky="nsew")
        self.t2d = self.tabs.add("2D HEATMAP")
        self.t3d = self.tabs.add("3D MODEL")
        self.traw = self.tabs.add("RAW DATA")
        self.text_editor = ctk.CTkTextbox(self.traw, font=("Consolas", 12))
        self.text_editor.pack(fill="both", expand=True)

        # Right Panel
        self.right = ctk.CTkFrame(self, width=300)
        self.right.grid(row=0, column=2, padx=(0, 20), pady=20, sticky="nsew")
        self.z_menu = ctk.CTkOptionMenu(self.right, values=["Винты (углы)", "2 вала (Л/П)", "3 вала (Tri-Z)", "4 вала (Quad-Z)"], command=self.refresh_recs)
        self.z_menu.set(self.settings.get("z_sys", "Винты (углы)"))
        self.z_menu.pack(pady=15, padx=10)

        self.p_label = ctk.CTkLabel(self.right, text="Шаг резьбы:")
        self.p_label.pack()
        self.p_menu = ctk.CTkOptionMenu(self.right, values=["0.7", "0.5", "0.8"], command=self.refresh_recs)
        self.p_menu.set(self.settings.get("pitch", "0.7"))
        self.p_menu.pack(pady=5)

        self.instr = ctk.CTkLabel(self.right, text="Ожидание данных...", justify="left")
        self.instr.pack(pady=20, padx=10)

        # Bottom Button
        self.btn = ctk.CTkButton(self, text="⚡ ВИЗУАЛИЗИРОВАТЬ", height=50, fg_color=styles.COLORS["dark"]["success"], command=self.run)
        self.btn.grid(row=1, column=0, columnspan=3, padx=20, pady=10, sticky="ew")

    def refresh_recs(self, _=None):
        if self.matrix is not None:
            txt, is_screws = logic.get_recs(self.matrix, self.z_menu.get(), float(self.p_menu.get()), int(self.gx.get()))
            self.instr.configure(text=txt)
            if is_screws: 
                self.p_label.pack(); self.p_menu.pack()
            else: 
                self.p_label.pack_forget(); self.p_menu.pack_forget()

    def run(self):
        raw = self.text_editor.get("0.0", "end").strip()
        self.matrix, err = logic.parse_points(raw, int(self.gx.get()), int(self.gy.get()))
        if self.matrix is not None:
            self.refresh_recs()
            self.draw()
            # Сохраняем настройки
            logic.save_settings({"host": self.ip.get(), "port": self.port.get(), "z_sys": self.z_menu.get(), "pitch": self.p_menu.get(), "grid_x": self.gx.get(), "grid_y": self.gy.get()})
        else: print(err)

    def draw(self):
        # Здесь логика отрисовки Matplotlib (аналогично v6.1)
        pass

if __name__ == "__main__":
    App().mainloop()