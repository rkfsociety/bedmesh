import customtkinter as ctk
from ui import elements_win
from utils import strings_win, styles_win

class LeftPanel(ctk.CTkScrollableFrame):
    def __init__(self, parent, settings, fetch_callback, toggle_log_cb):
        # Ширина 380
        super().__init__(parent, width=380, corner_radius=0, fg_color="#2b2b2b", 
                         scrollbar_button_color="#3d3d3d")
        
        self.toggle_log_cb = toggle_log_cb

        self.adv_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.adv_frame.pack(pady=(15, 0), padx=20, fill="x")

        self.adv_switch = ctk.CTkSwitch(
            self.adv_frame, text="Расширенные настройки", 
            font=("Segoe UI", 13, "bold"), command=self._on_adv_toggle
        )
        self.adv_switch.pack(anchor="w")

        # Дисклеймер теперь не переносится по середине слова
        self.warning_lbl = ctk.CTkLabel(
            self, 
            text="⚠️ ВНИМАНИЕ: Использование на свой страх и риск!\nАвтор не несет ответственности за любой ущерб,\nвызванный изменением параметров принтера.",
            font=("Segoe UI", 11, "bold"), text_color="#ff5555",
            justify="left", wraplength=340 
        )
        self.warning_lbl.pack(padx=25, pady=(8, 10), anchor="w")

        ctk.CTkLabel(self, text="—" * 25, text_color="#3d3d3d").pack(pady=5)

        ctk.CTkLabel(self, text=strings_win.SECTION_SSH, font=styles_win.FONTS["title"]).pack(pady=(10, 5))
        self.ip = elements_win.LabeledEntry(self, strings_win.LBL_IP, settings.get("host", ""))
        
        self.extra_settings_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.port = elements_win.LabeledEntry(self.extra_settings_frame, strings_win.LBL_PORT, settings.get("port", "2222"))
        self.user = elements_win.LabeledEntry(self.extra_settings_frame, strings_win.LBL_USER, settings.get("user", "root"))
        self.pwd = elements_win.LabeledEntry(self.extra_settings_frame, strings_win.LBL_PASS, settings.get("password", ""), show="*")
        self.p_mesh = elements_win.LabeledEntry(self.extra_settings_frame, strings_win.LBL_PATH, settings.get("path", ""))
        self.p_cfg = elements_win.LabeledEntry(self.extra_settings_frame, strings_win.LBL_PATH_CFG, settings.get("path_cfg", ""))
        
        ctk.CTkLabel(self.extra_settings_frame, text="\n" + strings_win.SECTION_GEOMETRY, font=styles_win.FONTS["ui_bold"]).pack(pady=(15, 5))
        self.bx = elements_win.LabeledEntry(self.extra_settings_frame, strings_win.LBL_BED_X, settings.get("bed_x", "250"))
        self.by = elements_win.LabeledEntry(self.extra_settings_frame, strings_win.LBL_BED_Y, settings.get("bed_y", "250"))
        self.gx = elements_win.LabeledEntry(self.extra_settings_frame, strings_win.LBL_GRID_X, settings.get("grid_x", "5"))
        self.gy = elements_win.LabeledEntry(self.extra_settings_frame, strings_win.LBL_GRID_Y, settings.get("grid_y", "5"))

        self.btn_fetch = ctk.CTkButton(
            self, text=strings_win.BTN_FETCH, command=fetch_callback, 
            fg_color="#3d3d3d", hover_color="#4d4d4d", height=45, font=styles_win.FONTS["ui_bold"]
        )
        self.btn_fetch.pack(pady=30, padx=25, fill="x")

        if settings.get("show_mutable", False):
            self.adv_switch.select()
            self.extra_settings_frame.pack(after=self.ip, fill="x")

    def _on_adv_toggle(self):
        is_active = self.adv_switch.get()
        if is_active: self.extra_settings_frame.pack(after=self.ip, fill="x")
        else: self.extra_settings_frame.pack_forget()
        self.toggle_log_cb(is_active)