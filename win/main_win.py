import customtkinter as ctk
import os
import sys
import threading
import matplotlib.pyplot as plt

from utils import logic_win, strings_win, storage_win, logger_win
from core import mesh_parser_win, transport_win
from ui import left_panel_win, right_panel_win, center_block_win

class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Настройка окна
        self.title(f"{strings_win.APP_TITLE} v{logic_win.VERSION}")
        self.center_window()
        self.set_app_icon()

        # Загрузка конфига
        self.settings = storage_win.load_settings()
        self.last_raw_data = ""
        self.matrix = None

        # Сетка
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Панели
        self.left_panel = left_panel_win.LeftPanel(
            self, self.settings, self.on_visualize_click, self.toggle_log_view
        )
        self.left_panel.grid(row=0, column=0, sticky="nsew")

        self.center_block = center_block_win.CenterBlock(self)
        self.center_block.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)

        self.right_panel = right_panel_win.RightPanel(
            self, 
            z_sys=self.settings.get("z_sys", "Винты (4шт)"),
            pitch=float(self.settings.get("pitch", 0.7)),
            refresh_cb=self.on_settings_changed
        )
        self.right_panel.grid(row=0, column=2, sticky="nsew", padx=(0, 10), pady=10)

        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        logger_win.info(f"Приложение запущено. Версия: {logic_win.VERSION}")

    def on_visualize_click(self):
        """Обработка клика: запуск в фоновом потоке"""
        # Блокируем кнопку на время загрузки (опционально)
        logger_win.info("Кнопка нажата. Запуск фонового потока SSH...")
        thread = threading.Thread(target=self.worker_fetch_data, daemon=True)
        thread.start()

    def worker_fetch_data(self):
        """Метод, работающий в фоновом потоке"""
        try:
            raw = transport_win.fetch_ssh(
                self.left_panel.ip.get(), 
                self.left_panel.port.get(),
                self.left_panel.user.get(), 
                self.left_panel.pwd.get(),
                self.left_panel.p_mesh.get()
            )
            
            if raw:
                self.last_raw_data = raw
                gx = self.left_panel.get_gx()
                gy = self.left_panel.get_gy()
                
                matrix, err = mesh_parser_win.parse_points(raw, gx, gy)
                
                if matrix is not None:
                    self.matrix = matrix
                    # Обновление UI должно быть в главном потоке
                    self.after(0, self.refresh_ui)
                else:
                    logger_win.error(f"Парсинг не удался: {err}")
            else:
                logger_win.warning("Данные с принтера не получены.")
        except Exception as e:
            logger_win.error(f"Ошибка в потоке: {e}")

    def refresh_ui(self):
        if self.matrix is None: return
        gx = self.left_panel.get_gx()
        self.center_block.update_display(self.matrix, gx, self.last_raw_data)
        self.right_panel.update_results(self.matrix, gx)
        logger_win.info("Интерфейс обновлен.")

    def on_settings_changed(self):
        self.settings["z_sys"] = self.right_panel.z_m.get()
        if self.right_panel.p_m.winfo_ismapped():
            self.settings["pitch"] = self.right_panel.p_m.get()
        storage_win.save_settings(self.settings)
        if self.matrix is not None:
            self.right_panel.update_results(self.matrix, self.left_panel.get_gx())

    def set_app_icon(self):
        icon_path = logic_win.resource_path("icon.ico")
        if os.path.exists(icon_path):
            try:
                if sys.platform.startswith('win'):
                    self.after(200, lambda: self.iconbitmap(icon_path))
            except: pass

    def center_window(self):
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        w, h = int(sw * 0.8), int(sh * 0.8)
        self.geometry(f"{w}x{h}+{(sw-w)//2}+{(sh-h)//2}")
        self.minsize(1200, 750)

    def toggle_log_view(self, state):
        self.settings["show_mutable"] = state
        storage_win.save_settings(self.settings)
        self.center_block.tabs.set(strings_win.TAB_RAW if state else strings_win.TAB_2D)

    def on_closing(self):
        plt.close('all')
        self.quit()
        self.destroy()
        os._exit(0)

if __name__ == "__main__":
    app = App()
    app.mainloop()