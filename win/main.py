import customtkinter as ctk
import logic, styles, ui_elements, strings, updater, viz
import matplotlib.pyplot as plt
import sys, os, ctypes
from tkinter import messagebox

# Поддержка высокого разрешения
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except: pass

ctk.set_appearance_mode("dark")

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        self.width, self.height = 1400, 950
        self.title(f"{strings.APP_TITLE} v{logic.VERSION}")
        self.center_window()
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        self.matrix = None
        self.settings = logic.load_settings()
        self.update_data = None

        try:
            icon_p = logic.resource_path("icon.ico")
            if os.path.exists(icon_p): self.iconbitmap(icon_p)
        except: pass

        self.grid_columnconfigure(1, weight=1); self.grid_rowconfigure(0, weight=1)

        # --- SIDEBAR ---
        self.sidebar = ctk.CTkFrame(self, width=300, corner_radius=0)
        self.sidebar.grid(row=0, column=0, rowspan=2, sticky="nsew")
        
        ctk.CTkLabel(self.sidebar, text=strings.SECTION_SSH, font=styles.FONTS["title"]).pack(pady=(20, 10))
        self.ip = ui_elements.LabeledEntry(self.sidebar, strings.LBL_IP, self.settings.get("host", "192.168.1.100"))
        self.port = ui_elements.LabeledEntry(self.sidebar, strings.LBL_PORT, self.settings.get("port", "22"))
        self.user = ui_elements.LabeledEntry(self.sidebar, strings.LBL_USER, self.settings.get("user", "pi"))
        self.pwd = ui_elements.LabeledEntry(self.sidebar, strings.LBL_PASS, self.settings.get("password", "raspberry"), show="*")
        self.path = ui_elements.LabeledEntry(self.sidebar, strings.LBL_PATH, self.settings.get("path", "...cfg"))
        ctk.CTkButton(self.sidebar, text=strings.BTN_FETCH, command=self.fetch, corner_radius=8).pack(pady=10, padx=20)
        
        ctk.CTkLabel(self.sidebar, text=strings.SECTION_GEOMETRY, font=styles.FONTS["ui_bold"]).pack(pady=(20, 5))
        self.bx = ui_elements.LabeledEntry(self.sidebar, strings.LBL_BED_X, self.settings.get("bed_x", "250"))
        self.by = ui_elements.LabeledEntry(self.sidebar, strings.LBL_BED_Y, self.settings.get("bed_y", "250"))
        self.gx = ui_elements.LabeledEntry(self.sidebar, strings.LBL_GRID_X, self.settings.get("grid_x", "5"))
        self.gy = ui_elements.LabeledEntry(self.sidebar, strings.LBL_GRID_Y, self.settings.get("grid_y", "5"))

        # --- TABS ---
        self.tabs = ctk.CTkTabview(self, corner_radius=15)
        self.tabs.grid(row=0, column=1, padx=20, pady=20, sticky="nsew")
        self.t2d = self.tabs.add(strings.TAB_2D)
        self.t3d = self.tabs.add(strings.TAB_3D)
        self.traw = self.tabs.add(strings.TAB_RAW)
        
        self.text_editor = ctk.CTkTextbox(self.traw, font=styles.FONTS["code"])
        self.text_editor.pack(fill="both", expand=True)

        # --- RIGHT PANEL ---
        self.right = ctk.CTkFrame(self, width=340); self.right.grid(row=0, column=2, padx=(0, 20), pady=20, sticky="nsew"); self.right.pack_propagate(False)
        ctk.CTkLabel(self.right, text=strings.SECTION_ALIGN, font=styles.FONTS["ui_bold"]).pack(pady=15)
        self.z_m = ctk.CTkOptionMenu(self.right, values=strings.Z_SYSTEMS, command=self.refresh_recs); self.z_m.set(self.settings.get("z_sys", strings.Z_SYSTEMS[0])); self.z_m.pack(pady=10, padx=20, fill="x")
        self.p_l = ctk.CTkLabel(self.right, text=strings.LBL_PITCH); self.p_l.pack(); self.p_m = ctk.CTkOptionMenu(self.right, values=["0.7", "0.5", "0.8"], command=self.refresh_recs); self.p_m.set(self.settings.get("pitch", "0.7")); self.p_m.pack(pady=5, padx=20, fill="x")
        
        self.rec_s = ctk.CTkScrollableFrame(self.right, fg_color="transparent")
        self.rec_s.pack(fill="both", expand=True, padx=5, pady=10)
        self.empty = ctk.CTkLabel(self.rec_s, text=strings.MSG_WAITING, font=("Segoe UI", 10), text_color="#555555"); self.empty.pack(pady=50)

        # --- КНОПКА ЗАПУСКА ---
        self.btn = ctk.CTkButton(self, text=strings.BTN_RUN, height=60, 
                                 fg_color=styles.COLORS["dark"]["success"], 
                                 font=styles.FONTS["title"], command=self.on_click, corner_radius=12)
        self.btn.grid(row=1, column=1, columnspan=2, padx=20, pady=(0, 20), sticky="ew")

        updater.check_for_updates(logic.VERSION, self.on_upd)

    def center_window(self):
        self.update_idletasks()
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        x, y = int((sw / 2) - (self.width / 2)), int((sh / 2) - (self.height / 2))
        self.geometry(f"{self.width}x{self.height}+{x}+{y}")

    def on_upd(self, v, data):
        self.update_data = data; self.btn.configure(text=f"UPDATE v{v}", fg_color="#007acc")

    def on_click(self):
        if self.update_data: updater.install_update(self.update_data)
        else: self.run()

    def fetch(self):
        try:
            res = logic.fetch_ssh(self.ip.get(), self.port.get(), self.user.get(), self.pwd.get(), self.path.get())
            self.text_editor.delete("0.0", "end"); self.text_editor.insert("end", res)
            self.run()
        except Exception as e: messagebox.showerror("SSH Error", str(e))

    def refresh_recs(self, _=None):
        if self.matrix is not None:
            data, is_s = logic.get_recs(self.matrix, self.z_m.get(), float(self.p_m.get()), int(self.gx.get()))
            for w in self.rec_s.winfo_children(): w.destroy()
            for i in data: ui_elements.RecCard(self.rec_s, i['name'], i['val'], i['turns'], i['dir'])
            if is_s: self.p_l.pack(); self.p_m.pack(pady=5, padx=20, fill="x")
            else: self.p_l.pack_forget(); self.p_m.pack_forget()

    def run(self):
        try:
            raw = self.text_editor.get("0.0", "end").strip()
            if not raw: return
            gx, gy = int(self.gx.get()), int(self.gy.get())
            self.matrix, err = logic.parse_points(raw, gx, gy)
            if self.matrix is not None:
                self.refresh_recs()
                bx, by = float(self.bx.get()), float(self.by.get())
                
                # РИСУЕМ КАРТЫ (Теперь стабильно и красиво)
                viz.draw_2d_map(self.t2d, self.matrix, bx, by, gx, gy)
                viz.draw_3d_pro(self.t3d, self.matrix, bx, by, gx, gy)
                
                self.tabs.set(strings.TAB_2D)
                logic.save_settings({"host": self.ip.get(), "port": self.port.get(), "user": self.user.get(), 
                                    "password": self.pwd.get(), "path": self.path.get(), "bed_x": self.bx.get(), 
                                    "bed_y": self.by.get(), "grid_x": self.gx.get(), "grid_y": self.gy.get(), 
                                    "z_sys": self.z_m.get(), "pitch": self.p_m.get()})
            else: messagebox.showwarning("Data Error", err)
        except Exception as e: messagebox.showerror("Error", str(e))

    def on_closing(self):
        plt.close('all'); self.destroy(); sys.exit(0)

if __name__ == "__main__": App().mainloop()