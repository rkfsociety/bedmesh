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

        # 1. Базовая настройка
        self.title(f"{strings_win.APP_TITLE} v{logic_win.VERSION}")
        self.center_window()
        self.set_app_icon()

        # 2. Данные и настройки
        self.settings = storage_win.load_settings()
        self.last_raw_data = "" # Здесь хранятся скачанные данные
        self.matrix = None

        # 3. Сетка
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Центр
        self.center_block = center_block_win.CenterBlock(self)
        self.center_block.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)

        # Левая панель
        self.left_panel = left_panel_win.LeftPanel(
            self, self.settings, self.on_visualize_click, self.toggle_log_view
        )
        self.left_panel.grid(row=0, column=0, sticky="nsew")

        # Правая панель
        self.right_panel = right_panel_win.RightPanel(
            self, 
            z_sys=self.settings.get("z_sys", "Винты (4шт)"),
            pitch=float(self.settings.get("pitch", 0.7)),
            refresh_cb=self.on_settings_changed
        )
        self.right_panel.grid(row=0, column=2, sticky="nsew", padx=(0, 10), pady=10)

        # Проверка состояния при старте
        initial_adv = self.settings.get("show_mutable", False)
        self.toggle_log_view(initial_adv)

        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        logger_win.info(f"Приложение запущено. Версия: {logic_win.VERSION}")

    def toggle_log_view(self, state):
        """Управляет видимостью вкладки без повторного запроса к SSH"""
        self.settings["show_mutable"] = state
        storage_win.save_settings(self.settings)
        
        if state:
            self.center_block.show_raw_tab()
            # ВАЖНО: Если данные уже были загружены ранее, просто отображаем их
            if self.last_raw_data:
                gx = self.left_panel.get_gx()
                self.center_block.update_display(self.matrix, gx, self.last_raw_data)
        else:
            self.center_block.hide_raw_tab()
            
        logger_win.info(f"Режим расширенных настроек: {state}. Вкладка RAW обновлена.")

    def set_app_icon(self):
        icon_path = logic_win.resource_path("icon.ico")
        if os.path.exists(icon_path):
            try:
                if sys.platform.startswith('win'):
                    self.after(200, lambda: self.iconbitmap(icon_path))
            except Exception as e:
                logger_win.error(f"Ошибка иконки: {e}")

    def on_visualize_click(self):
        logger_win.info("Запуск потока SSH...")
        thread = threading.Thread(target=self.worker_fetch_data, daemon=True)
        thread.start()

    def worker_fetch_data(self):
        try:
            raw = transport_win.fetch_ssh(
                self.left_panel.ip.get(), self.left_panel.port.get(),
                self.left_panel.user.get(), self.left_panel.pwd.get(),
                self.left_panel.p_mesh.get()
            )
            if raw:
                self.last_raw_data = raw # Сохраняем текст файла в память
                gx, gy = self.left_panel.get_gx(), self.left_panel.get_gy()
                matrix, err = mesh_parser_win.parse_points(raw, gx, gy)
                if matrix is not None:
                    self.matrix = matrix
                    self.after(0, self.refresh_ui)
            else:
                logger_win.warning("SSH не вернул данных.")
        except Exception as e:
            logger_win.error(f"Ошибка в воркере: {e}")

    def refresh_ui(self):
        if self.matrix is None: return
        self.center_block.update_display(self.matrix, self.left_panel.get_gx(), self.last_raw_data)
        self.right_panel.update_results(self.matrix, self.left_panel.get_gx())

    def on_settings_changed(self):
        self.settings["z_sys"] = self.right_panel.z_m.get()
        if self.right_panel.p_m.winfo_ismapped():
            self.settings["pitch"] = self.right_panel.p_m.get()
        storage_win.save_settings(self.settings)
        if self.matrix is not None:
            self.right_panel.update_results(self.matrix, self.left_panel.get_gx())

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