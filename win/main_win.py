import customtkinter as ctk
import os
import sys
import threading
import matplotlib.pyplot as plt
from tkinter import messagebox
import ctypes 

from utils import logic_win, strings_win, storage_win, logger_win, styles_win, updater_win
from core import mesh_parser_win, transport_win, backup_win, config_editor_win
from ui import left_panel_win, right_panel_win, center_block_win

class App(ctk.CTk):
    def __init__(self):
        styles_win.apply_global_styles()
        super().__init__()

        self.settings = storage_win.load_settings()
        self.title(f"{strings_win.APP_TITLE} v{logic_win.VERSION}")
        
        self.set_app_icon()
        self.center_window()

        self.last_raw_mutable = ""
        self.last_raw_config = ""
        self.matrix = None
        self.config_editor = None 

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.center_block = center_block_win.CenterBlock(self)
        self.center_block.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)

        self.left_panel = left_panel_win.LeftPanel(self, self.settings, self.on_visualize_click, self.toggle_log_view)
        self.left_panel.grid(row=0, column=0, sticky="nsew")

        self.right_panel = right_panel_win.RightPanel(self, None, 0.7, self.on_settings_changed)
        self.right_panel.grid(row=0, column=2, sticky="nsew", padx=(0, 10), pady=10)

        updater_win.check_for_updates(logic_win.VERSION, self.on_update_found)
        self.toggle_log_view(self.settings.get("show_mutable", False))
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    def toggle_log_view(self, state):
        self.settings["show_mutable"] = state
        storage_win.save_settings(self.settings)
        if state:
            self.center_block.show_raw_tab()
            self.center_block.show_config_editor_tab(self.on_save_config_request, self.on_restore_backup_request)
            if self.config_editor:
                data = self.config_editor.get_config_parameters()
                self.center_block.fill_config_fields(data)
            
            if self.last_raw_mutable:
                self.center_block.update_display(self.matrix, int(self.settings["grid_x"]), self.last_raw_mutable)
        else:
            self.center_block.hide_raw_tab()
            self.center_block.hide_config_editor_tab()

    def on_visualize_click(self):
        self.update_settings_from_ui()
        storage_win.save_settings(self.settings)
        self.right_panel.set_status("busy")
        threading.Thread(target=self.worker_fetch_data, daemon=True).start()

    def worker_fetch_data(self):
        h, p, u, pw = self.settings["host"], self.settings["port"], self.settings["user"], self.settings["password"]
        p_mesh, p_cfg = self.settings["path"], self.settings["path_cfg"]
        try:
            # Инициализация транспорта и редактора
            transport = transport_win.SSHTransport(h, int(p), u, pw)
            self.config_editor = config_editor_win.ConfigEditor(transport)
            
            # Бэкапы
            backup_win.auto_backup_if_missing(h, p, u, pw, p_cfg)
            backups = backup_win.get_backup_list(h, p, u, pw, p_cfg)
            self.after(0, lambda: self.center_block.update_backup_list(backups))
            
            # Подтягиваем параметры в редактор
            config_params = self.config_editor.get_config_parameters()
            if config_params:
                self.after(0, lambda: self.center_block.fill_config_fields(config_params))

            # Читаем карту стола
            raw_m = transport.read_file(p_mesh)
            if raw_m:
                self.last_raw_mutable = raw_m
                gx, gy = int(self.settings["grid_x"]), int(self.settings["grid_y"])
                matrix, _ = mesh_parser_win.parse_points(raw_m, gx, gy)
                if matrix is not None:
                    self.matrix = matrix
                    self.after(0, lambda: self.center_block.update_display(matrix, gx, raw_m))
                    self.after(0, lambda: self.right_panel.update_results(matrix, gx))
                    self.after(0, lambda: self.right_panel.set_status("ready"))
            else: self.after(0, lambda: self.right_panel.set_status("error"))
        except Exception as e:
            logger_win.error(f"Worker error: {e}")
            self.after(0, lambda: self.right_panel.set_status("error"))

    def on_save_config_request(self):
        if not self.config_editor:
            messagebox.showerror("Ошибка", "Сначала подключитесь к принтеру")
            return
        new_params = self.center_block.get_all_fields()
        if self.config_editor.save_config(new_params):
            messagebox.showinfo("Успех", "Конфигурация сохранена и принтер перезагружен!")
        else:
            messagebox.showerror("Ошибка", "Не удалось сохранить файл.")

    def on_restore_backup_request(self, filename):
        if not self.config_editor: return
        h, p, u, pw = self.settings["host"], self.settings["port"], self.settings["user"], self.settings["password"]
        p_cfg = self.settings["path_cfg"]
        if messagebox.askyesno("Подтверждение", f"Восстановить {filename}?"):
            if backup_win.restore_backup(h, p, u, pw, p_cfg, filename):
                messagebox.showinfo("Готово", "Восстановлено!")
                data = self.config_editor.get_config_parameters()
                self.center_block.fill_config_fields(data)

    def update_settings_from_ui(self):
        self.settings.update({
            "host": self.left_panel.ip.get(), "port": self.left_panel.port.get(),
            "user": self.left_panel.user.get(), "password": self.left_panel.pwd.get(),
            "path": self.left_panel.p_mesh.get(), "path_cfg": self.left_panel.p_cfg.get(),
            "grid_x": self.left_panel.gx.get(), "grid_y": self.left_panel.gy.get(),
            "bed_x": self.left_panel.bx.get(), "bed_y": self.left_panel.by.get(),
        })

    def on_settings_changed(self):
        if self.matrix is not None: self.right_panel.update_results(self.matrix, int(self.left_panel.gx.get()))
    def on_update_found(self, new_ver, data):
        self.after(0, lambda: self.right_panel.show_update_available(lambda: updater_win.install_update(data)))
    def center_window(self):
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        w, h = int(sw * 0.9), int(sh * 0.85)
        self.geometry(f"{w}x{h}+{(sw-w)//2}+{(sh-h)//2}")
        self.minsize(1350, 800)
    def on_closing(self):
        plt.close('all'); self.quit(); self.destroy(); os._exit(0)
    def set_app_icon(self):
        icon_path = logic_win.resource_path("icon.ico")
        if os.path.exists(icon_path):
            try:
                myappid = f'mycompany.myproduct.subproduct.{logic_win.VERSION}'
                ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
                self.iconbitmap(icon_path)
            except Exception: pass

if __name__ == "__main__":
    app = App(); app.mainloop()