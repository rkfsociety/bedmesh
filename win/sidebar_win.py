import customtkinter as ctk
import ui_elements_win, strings_win, styles_win

class Sidebar(ctk.CTkScrollableFrame):
    def __init__(self, parent, settings, fetch_callback, toggle_log_cb):
        super().__init__(parent, width=340, corner_radius=0, fg_color="#2b2b2b", 
                         scrollbar_button_color="#3d3d3d")
        
        # Переключатель
        self.adv_switch = ctk.CTkSwitch(self, text="", command=lambda: toggle_log_cb(self.adv_switch.get()))
        self.adv_switch.pack(pady=(15, 5), padx=20, anchor="w")
        self.adv_switch.bind("<Enter>", lambda e: self.adv_switch.configure(text="Расширенные настройки"))
        self.adv_switch.bind("<Leave>", lambda e: self.adv_switch.configure(text=""))

        ctk.CTkLabel(self, text="—" * 20, text_color="#3d3d3d").pack(pady=5)

        # SSH
        ctk.CTkLabel(self, text=strings_win.SECTION_SSH, font=styles_win.FONTS["title"]).pack(pady=(5, 5))
        self.ip = ui_elements_win.LabeledEntry(self, strings_win.LBL_IP, settings.get("host", ""))
        self.port = ui_elements_win.LabeledEntry(self, strings_win.LBL_PORT, settings.get("port", "2222"))
        self.user = ui_elements_win.LabeledEntry(self, strings_win.LBL_USER, settings.get("user", "root"))
        self.pwd = ui_elements_win.LabeledEntry(self, strings_win.LBL_PASS, settings.get("password", "rockchip"), show="*")
        
        self.p_mesh = ui_elements_win.LabeledEntry(self, strings_win.LBL_PATH, settings.get("path", "/userdata/app/gk/printer_mutable.cfg"))
        self.p_cfg = ui_elements_win.LabeledEntry(self, strings_win.LBL_PATH_CFG, settings.get("path_cfg", "/userdata/app/gk/printer.cfg"))
        
        ctk.CTkButton(self, text=strings_win.BTN_FETCH, command=fetch_callback, fg_color="#3d3d3d", height=35).pack(pady=10, padx=25, fill="x")
        
        # Геометрия
        ctk.CTkLabel(self, text=strings_win.SECTION_GEOMETRY, font=styles_win.FONTS["ui_bold"]).pack(pady=(10, 5))
        self.bx = ui_elements_win.LabeledEntry(self, strings_win.LBL_BED_X, settings.get("bed_x", "250"))
        self.by = ui_elements_win.LabeledEntry(self, strings_win.LBL_BED_Y, settings.get("bed_y", "250"))
        self.gx = ui_elements_win.LabeledEntry(self, strings_win.LBL_GRID_X, settings.get("grid_x", "5"))
        self.gy = ui_elements_win.LabeledEntry(self, strings_win.LBL_GRID_Y, settings.get("grid_y", "5"))

    def get_data(self):
        return {
            "host": self.ip.get(), "port": self.port.get(), "user": self.user.get(), "password": self.pwd.get(),
            "path": self.p_mesh.get(), "path_cfg": self.p_cfg.get(), "bed_x": self.bx.get(), "bed_y": self.by.get(),
            "grid_x": self.gx.get(), "grid_y": self.gy.get()
        }