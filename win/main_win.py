import customtkinter as ctk
import os
import sys
import matplotlib.pyplot as plt

# Импорты из наших новых модулей
from utils import logic_win, strings_win, storage_win
from core import mesh_parser_win, transport_win
from ui import left_panel_win, right_panel_win, center_block_win

class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        # 1. Основные настройки окна
        self.title(f"{strings_win.APP_TITLE} v{logic_win.VERSION}")
        self.center_window()
        self.set_app_icon()

        # 2. Загрузка конфигурации
        self.settings = storage_win.load_settings()
        
        # Состояние данных
        self.last_raw_data = ""
        self.matrix = None

        # 3. Настройка сетки (Layout)
        # 0: Левая панель (фиксированная) | 1: Центр (растягивается) | 2: Правая панель (фиксированная)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # --- ЛЕВАЯ ПАНЕЛЬ (Ввод данных и SSH) ---
        self.left_panel = left_panel_win.LeftPanel(
            self, 
            settings=self.settings,
            fetch_callback=self.on_visualize, 
            toggle_log_cb=self.toggle_log_view
        )
        self.left_panel.grid(row=0, column=0, sticky="nsew")

        # --- ЦЕНТРАЛЬНЫЙ БЛОК (Карты и Текст) ---
        self.center_block = center_block_win.CenterBlock(self)
        self.center_block.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)

        # --- ПРАВАЯ ПАНЕЛЬ (Аналитика и Статистика) ---
        self.right_panel = right_panel_win.RightPanel(
            self, 
            z_sys=self.settings.get("z_sys", "Винты (4шт)"),
            pitch=float(self.settings.get("pitch", 0.7)),
            refresh_cb=self.on_settings_changed
        )
        self.right_panel.grid(row=0, column=2, sticky="nsew", padx=(0, 10), pady=10)

        # 4. Протоколы и завершение инициализации
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # Если в настройках было указано показывать лог — активируем
        if self.settings.get("show_mutable", False):
            # В новой структуре вкладка RAW уже в CenterBlock, 
            # здесь мы можем просто переключить индекс таба если нужно
            self.center_block.tabs.set(strings_win.TAB_RAW)

    def set_app_icon(self):
        """Установка иконки приложения"""
        icon_path = logic_win.resource_path("icon.ico")
        if os.path.exists(icon_path):
            try:
                if sys.platform.startswith('win'):
                    self.after(200, lambda: self.iconbitmap(icon_path))
                else:
                    from PIL import Image, ImageTk
                    img = ImageTk.PhotoImage(Image.open(icon_path))
                    self.wm_iconphoto(True, img)
            except:
                pass

    def center_window(self):
        """Центрирование окна на экране"""
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        w, h = int(sw * 0.8), int(sh * 0.8)
        x = (sw - w) // 2
        y = (sh - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")
        self.minsize(1200, 750)

    def on_visualize(self):
        """Логика кнопки 'Получить данные'"""
        try:
            # Сбор данных SSH из левой панели
            raw = transport_win.fetch_ssh(
                self.left_panel.ip.get(), self.left_panel.port.get(),
                self.left_panel.user.get(), self.left_panel.pwd.get(),
                self.left_panel.p_mesh.get()
            )
            
            if not raw:
                print("Ошибка: Данные не получены")
                return

            self.last_raw_data = raw
            gx = self.left_panel.get_gx()
            gy = self.left_panel.get_gy()
            
            # Парсинг
            matrix, err = mesh_parser_win.parse_points(raw, gx, gy)
            
            if matrix is not None:
                self.matrix = matrix
                self.refresh_ui()
            else:
                print(f"Ошибка парсера: {err}")
                
        except Exception as e:
            print(f"Критическая ошибка при визуализации: {e}")

    def on_settings_changed(self):
        """Срабатывает при изменении параметров в RightPanel (выбор механики/винтов)"""
        # Синхронизируем настройки для сохранения
        self.settings["z_sys"] = self.right_panel.z_m.get()
        
        # Сохраняем шаг резьбы только если он отображается (не валы)
        if self.right_panel.p_m.winfo_ismapped():
            self.settings["pitch"] = self.right_panel.p_m.get()
            
        storage_win.save_settings(self.settings)
        
        # Если матрица уже в памяти — просим правую панель пересчитать результаты
        if self.matrix is not None:
            self.right_panel.update_results(self.matrix, self.left_panel.get_gx())

    def refresh_ui(self):
        """Полное обновление всех блоков интерфейса при получении новых данных"""
        if self.matrix is None: return
        
        gx = self.left_panel.get_gx()
        
        # 1. Обновляем центр (карту и текст)
        self.center_block.update_display(self.matrix, gx, self.last_raw_data)
        
        # 2. Обновляем правую панель (анализ)
        self.right_panel.update_results(self.matrix, gx)

    def toggle_log_view(self, state):
        """Управление видимостью расширенных настроек и логов"""
        self.settings["show_mutable"] = state
        storage_win.save_settings(self.settings)
        
        # Переключаем вкладку в центре если включили расширенный режим
        if state:
            self.center_block.tabs.set(strings_win.TAB_RAW)
        else:
            self.center_block.tabs.set(strings_win.TAB_2D)

    def on_closing(self):
        """Корректный выход из приложения"""
        plt.close('all')
        self.quit()
        self.destroy()
        os._exit(0)

if __name__ == "__main__":
    app = App()
    app.mainloop()