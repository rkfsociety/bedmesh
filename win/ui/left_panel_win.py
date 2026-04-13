import customtkinter as ctk
from ui import elements_win
from utils import strings_win, styles_win

class LeftPanel(ctk.CTkScrollableFrame):
    def __init__(self, parent, settings, fetch_callback, toggle_log_cb):
        super().__init__(parent, width=340, corner_radius=0, fg_color="#2b2b2b", 
                         scrollbar_button_color="#3d3d3d")
        
        self.toggle_log_cb = toggle_log_cb

        # --- 1. ПЕРЕКЛЮЧАТЕЛЬ РЕЖИМА (Теперь в самом верху) ---
        self.adv_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.adv_frame.pack(pady=(15, 5), padx=20, fill="x")

        self.adv_switch = ctk.CTkSwitch(
            self.adv_frame, 
            text="Расширенные настройки", 
            font=styles_win.FONTS["ui_bold"],
            command=self._on_adv_toggle
        )
        self.adv_switch.pack(anchor="w")

        # Разделитель под свитчем
        self.top_sep = ctk.CTkLabel(self, text="—" * 20, text_color="#3d3d3d")
        self.top_sep.pack(pady=5)

        # --- 2. Блок SSH ---
        ctk.CTkLabel(self, text=strings_win.SECTION_SSH, font=styles_win.FONTS["title"]).pack(pady=(10, 5))
        
        # IP всегда виден
        self.ip = elements_win.LabeledEntry(self, strings_win.LBL_IP, settings.get("host", "192.168.1.1"))
        
        # Контейнер для скрытых полей SSH
        self.extra_ssh_frame = ctk.CTkFrame(self, fg_color="transparent")
        
        self.port = elements_win.LabeledEntry(self.extra_ssh_frame, strings_win.LBL_PORT, settings.get("port", "2222"))
        self.user = elements_win.LabeledEntry(self.extra_ssh_frame, strings_win.LBL_USER, settings.get("user", "root"))
        self.pwd = elements_win.LabeledEntry(self.extra_ssh_frame, strings_win.LBL_PASS, settings.get("password", "rockchip"), show="*")
        
        self.p_mesh = elements_win.LabeledEntry(self.extra_ssh_frame, strings_win.LBL_PATH, settings.get("path", "/userdata/app/gk/printer_mutable.cfg"))
        self.p_cfg = elements_win.LabeledEntry(self.extra_ssh_frame, strings_win.LBL_PATH_CFG, settings.get("path_cfg", "/userdata/app/gk/printer.cfg"))
        
        # Кнопка получения данных (Всегда видна)
        ctk.CTkButton(
            self, 
            text=strings_win.BTN_FETCH, 
            command=fetch_callback, 
            fg_color="#3d3d3d", 
            height=35,
            font=styles_win.FONTS["ui_bold"]
        ).pack(pady=10, padx=25, fill="x")
        
        # --- 3. Блок Геометрия ---
        ctk.CTkLabel(self, text=strings_win.SECTION_GEOMETRY, font=styles_win.FONTS["ui_bold"]).pack(pady=(10, 5))
        self.bx = elements_win.LabeledEntry(self, strings_win.LBL_BED_X, settings.get("bed_x", "250"))
        self.by = elements_win.LabeledEntry(self, strings_win.LBL_BED_Y, settings.get("bed_y", "250"))
        self.gx = elements_win.LabeledEntry(self, strings_win.LBL_GRID_X, settings.get("grid_x", "5"))
        self.gy = elements_win.LabeledEntry(self, strings_win.LBL_GRID_Y, settings.get("grid_y", "5"))

        # Установка начального состояния
        if settings.get("show_mutable", False):
            self.adv_switch.select()
            self.extra_ssh_frame.pack(after=self.ip, fill="x")

    def _on_adv_toggle(self):
        """Логика показа/скрытия полей при клике на свитч"""
        is_active = self.adv_switch.get()
        
        if is_active:
            self.extra_ssh_frame.pack(after=self.ip, fill="x")
        else:
            self.extra_ssh_frame.pack_forget()
        
        # Уведомляем Main о смене режима
        self.toggle_log_cb(is_active)

    def get_gx(self):
        try: return int(self.gx.get())
        except: return 5

    def get_gy(self):
        try: return int(self.gy.get())
        except: return 5