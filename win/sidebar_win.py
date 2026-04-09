import customtkinter as ctk
import ui_elements_win, strings_win, styles_win

class Sidebar(ctk.CTkFrame):
    def __init__(self, parent, settings, fetch_callback):
        super().__init__(parent, width=360, corner_radius=0)
        self.pack_propagate(False) # Фиксируем ширину 360px
        
        # Секция SSH
        ctk.CTkLabel(self, text=strings_win.SECTION_SSH, font=styles_win.FONTS["title"]).pack(pady=(15, 5))
        
        # IP оставляем пустым, так как он индивидуален
        self.ip = ui_elements_win.LabeledEntry(self, strings_win.LBL_IP, settings.get("host", ""))
        
        # Новые базовые значения для порта, логина и пароля
        self.port = ui_elements_win.LabeledEntry(self, strings_win.LBL_PORT, settings.get("port", "2222"))
        self.user = ui_elements_win.LabeledEntry(self, strings_win.LBL_USER, settings.get("user", "root"))
        self.pwd = ui_elements_win.LabeledEntry(self, strings_win.LBL_PASS, settings.get("password", "rockchip"), show="*")
        
        # Новые базовые пути к файлам конфигурации
        self.p_mesh = ui_elements_win.LabeledEntry(self, strings_win.LBL_PATH, 
                                                   settings.get("path", "/userdata/app/gk/printer_mutable.cfg"))
        self.p_cfg = ui_elements_win.LabeledEntry(self, strings_win.LBL_PATH_CFG, 
                                                  settings.get("path_cfg", "/userdata/app/gk/printer.cfg"))
        
        # Кнопка получения данных
        ctk.CTkButton(self, text=strings_win.BTN_FETCH, command=fetch_callback, fg_color="#3d3d3d", height=35).pack(pady=10, padx=25, fill="x")
        
        # Секция Геометрии
        ctk.CTkLabel(self, text=strings_win.SECTION_GEOMETRY, font=styles_win.FONTS["ui_bold"]).pack(pady=(10, 5))
        self.bx = ui_elements_win.LabeledEntry(self, strings_win.LBL_BED_X, settings.get("bed_x", "250"))
        self.by = ui_elements_win.LabeledEntry(self, strings_win.LBL_BED_Y, settings.get("bed_y", "250"))
        self.gx = ui_elements_win.LabeledEntry(self, strings_win.LBL_GRID_X, settings.get("grid_x", "5"))
        self.gy = ui_elements_win.LabeledEntry(self, strings_win.LBL_GRID_Y, settings.get("grid_y", "5"))

    def get_data(self):
        """Метод для сбора всех данных из полей"""
        return {
            "host": self.ip.get(), 
            "port": self.port.get(),
            "user": self.user.get(), 
            "password": self.pwd.get(),
            "path": self.p_mesh.get(), 
            "path_cfg": self.p_cfg.get(),
            "bed_x": self.bx.get(), 
            "bed_y": self.by.get(),
            "grid_x": self.gx.get(), 
            "grid_y": self.gy.get()
        }