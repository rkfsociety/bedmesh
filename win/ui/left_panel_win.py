import customtkinter as ctk
from ui import elements_win
from utils import strings_win, styles_win

class LeftPanel(ctk.CTkScrollableFrame):
    def __init__(self, parent, settings, fetch_callback, toggle_log_cb):
        super().__init__(parent, width=340, corner_radius=0, fg_color="#2b2b2b", 
                         scrollbar_button_color="#3d3d3d")
        
        # --- Блок SSH ---
        ctk.CTkLabel(self, text=strings_win.SECTION_SSH, font=styles_win.FONTS["title"]).pack(pady=(15, 5))
        
        self.ip = elements_win.LabeledEntry(self, strings_win.LBL_IP, settings.get("host", "192.168.1.1"))
        self.port = elements_win.LabeledEntry(self, strings_win.LBL_PORT, settings.get("port", "22"))
        self.user = elements_win.LabeledEntry(self, strings_win.LBL_USER, settings.get("user", "root"))
        self.pwd = elements_win.LabeledEntry(self, strings_win.LBL_PASS, settings.get("password", ""), show="*")
        
        self.p_mesh = elements_win.LabeledEntry(self, strings_win.LBL_PATH, settings.get("path", "/userdata/app/gk/printer_mutable.cfg"))
        self.p_cfg = elements_win.LabeledEntry(self, strings_win.LBL_PATH_CFG, settings.get("path_cfg", "/userdata/app/gk/printer.cfg"))
        
        ctk.CTkButton(
            self, 
            text=strings_win.BTN_FETCH, 
            command=fetch_callback, 
            fg_color="#3d3d3d", 
            height=35,
            font=styles_win.FONTS["ui_bold"]
        ).pack(pady=10, padx=25, fill="x")
        
        # --- Блок Геометрия ---
        ctk.CTkLabel(self, text=strings_win.SECTION_GEOMETRY, font=styles_win.FONTS["ui_bold"]).pack(pady=(10, 5))
        self.bx = elements_win.LabeledEntry(self, strings_win.LBL_BED_X, settings.get("bed_x", "250"))
        self.by = elements_win.LabeledEntry(self, strings_win.LBL_BED_Y, settings.get("bed_y", "250"))
        self.gx = elements_win.LabeledEntry(self, strings_win.LBL_GRID_X, settings.get("grid_x", "5"))
        self.gy = elements_win.LabeledEntry(self, strings_win.LBL_GRID_Y, settings.get("grid_y", "5"))

        ctk.CTkLabel(self, text="—" * 20, text_color="#3d3d3d").pack(pady=10)

        # --- Блок расширенных настроек ---
        self.adv_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.adv_frame.pack(pady=(5, 15), padx=20, fill="x")

        self.adv_switch = ctk.CTkSwitch(
            self.adv_frame, 
            text="Расширенные настройки", 
            font=styles_win.FONTS["ui"],
            command=lambda: toggle_log_cb(self.adv_switch.get())
        )
        
        if settings.get("show_mutable", False):
            self.adv_switch.select()
            
        self.adv_switch.pack(anchor="w")

    def get_gx(self):
        try: return int(self.gx.get())
        except: return 5

    def get_gy(self):
        try: return int(self.gy.get())
        except: return 5