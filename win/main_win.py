import customtkinter as ctk
import os
import sys
import threading
import matplotlib.pyplot as plt

from utils import logic_win, strings_win, storage_win, logger_win, styles_win
from core import mesh_parser_win, transport_win
from ui import left_panel_win, right_panel_win, center_block_win

class App(ctk.CTk):
    def __init__(self):
        # 1. Принудительно применяем DARK режим до создания окна
        styles_win.apply_global_styles()
        
        super().__init__()

        # 2. Загрузка настроек
        self.settings = storage_win.load_settings()
        
        # 3. Базовая настройка окна
        self.title(f"{strings_win.APP_TITLE} v{logic_win.VERSION}")
        self.center_window()
        self.set_app_icon()

        self.last_raw_data = ""
        self.matrix = None

        # 4. Сетка интерфейса
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Центр
        self.center_block = center_block_win.CenterBlock(self)
        self.center_block.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)

        # Левая панель
        self.left_panel = left_panel_win.LeftPanel(
            self, 
            settings=self.settings, 
            fetch_callback=self.on_visualize_click, 
            toggle_log_cb=self.toggle_log_view
        )
        self.left_panel.grid(row=0, column=0, sticky="nsew")

        # Правая панель
        self.right_panel = right_panel_win.RightPanel(
            self, 
            z_sys=None,
            pitch=0.7,
            refresh_cb=self.on_settings_changed
        )
        self.right_panel.grid(row=0, column=2, sticky="nsew", padx=(0, 10), pady=10)

        # Применение состояния расширенных настроек при старте
        initial_adv = self.settings.get("show_mutable", False)
        self.toggle_log_view(initial_adv)

        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        logger_win.info(f"Приложение v{logic_win.VERSION} запущено в режиме FORCE DARK.")

    def toggle_log_view(self, state):
        self.settings["show_mutable"] = state
        storage_win.save_settings(self.settings)
        if state:
            self.center_block.show_raw_tab()
            if self.last_raw_data:
                self.center_block.update_display(self.matrix, self.left_panel.get_gx(), self.last_raw_data)
        else:
            self.center_block.hide_raw_tab()

    def set_app_icon(self):
        icon_path = logic_win.resource_path("icon.ico")
        if os.path.exists(icon_path):
            try:
                if sys.platform.startswith('win'):
                    self.after(200, lambda: self.iconbitmap(icon_path))
            except: pass

    def on_visualize_click(self):
        self.update_settings_from_ui()
        storage_win.save_settings(self.settings)
        thread = threading.Thread(target=self.worker_fetch_data, daemon=True)
        thread.start()

    def update_settings_from_ui(self):
        self.settings["host"] = self.left_panel.ip.get()
        self.settings["port"] = self.left_panel.port.get()
        self.settings["user"] = self.left_panel.user.get()
        self.settings["password"] = self.left_panel.pwd.get()
        self.settings["path"] = self.left_panel.p_mesh.get()
        self.settings["path_cfg"] = self.left_panel.p_cfg.get()
        self.settings["bed_x"] = self.left_panel.bx.get()
        self.settings["bed_y"] = self.left_panel.by.get()
        self.settings["grid_x"] = self.left_panel.gx.get()
        self.settings["grid_y"] = self.left_panel.gy.get()

    def worker_fetch_data(self):
        try:
            raw = transport_win.fetch_ssh(
                self.settings["host"], self.settings["port"],
                self.settings["user"], self.settings["password"],
                self.settings["path"]
            )
            if raw:
                self.last_raw_data = raw
                gx = int(self.settings["grid_x"])
                gy = int(self.settings["grid_y"])
                matrix, err = mesh_parser_win.parse_points(raw, gx, gy)
                if matrix is not None:
                    self.matrix = matrix
                    self.after(0, self.refresh_ui)
            else:
                logger_win.warning("Данные не получены.")
        except Exception as e:
            logger_win.error(f"Ошибка в воркере: {e}")

    def refresh_ui(self):
        if self.matrix is None: return
        gx = int(self.settings["grid_x"])
        self.center_block.update_display(self.matrix, gx, self.last_raw_data)
        self.right_panel.update_results(self.matrix, gx)

    def on_settings_changed(self):
        if self.matrix is not None:
            self.right_panel.update_results(self.matrix, int(self.left_panel.gx.get()))

    def center_window(self):
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        w, h = int(sw * 0.8), int(sh * 0.8)
        self.geometry(f"{w}x{h}+{(sw-w)//2}+{(sh-h)//2}")
        self.minsize(1200, 750)

    def on_closing(self):
        plt.close('all')
        self.quit()
        self.destroy()
        os._exit(0)

if __name__ == "__main__":
    app = App()
    app.mainloop()