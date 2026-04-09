import customtkinter as ctk
import logic_win, strings_win, updater_win, backup_win, map2d_win, config_win, transport_win, mesh_parser_win, storage_win
from sidebar_win import Sidebar
from tabs_win import SettingsTab
from analysis_win import AnalysisPanel
import sys, os, ctypes, signal
from tkinter import messagebox
import matplotlib.pyplot as plt

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.width, self.height = 1400, 950
        self.title(f"{strings_win.APP_TITLE} v{logic_win.VERSION}")
        self.center_window()
        self.set_app_icon()
        
        self.matrix, self.cfg_content = None, ""
        self.settings = storage_win.load_settings()
        
        self.grid_columnconfigure(1, weight=1); self.grid_rowconfigure(0, weight=1)
        self.init_ui()
        
        # Передаем ссылку на метод закрытия в апдейтер, если это нужно
        updater_win.check_for_updates(logic_win.VERSION, self.show_update_notify)

    def init_ui(self):
        self.sidebar = Sidebar(self, self.settings, self.fetch)
        self.sidebar.grid(row=0, column=0, rowspan=2, sticky="nsew")

        self.tabs = ctk.CTkTabview(self, corner_radius=15)
        self.tabs.grid(row=0, column=1, padx=20, pady=20, sticky="nsew")
        self.t2d, self.traw, self.tset_frame = self.tabs.add(strings_win.TAB_2D), self.tabs.add(strings_win.TAB_RAW), self.tabs.add("ПАРАМЕТРЫ")

        self.text_editor = ctk.CTkTextbox(self.traw, font=("Consolas", 12))
        self.text_editor.pack(fill="both", expand=True)
        self.settings_tab = SettingsTab(self.tset_frame, self.create_backup, self.restore_backup, self.save_cfg)
        self.settings_tab.pack(fill="both", expand=True)

        self.analysis = AnalysisPanel(self, self.settings.get("z_sys", strings_win.Z_SYSTEMS[0]), self.settings.get("pitch", "0.7"), self.refresh_recs)
        self.analysis.grid(row=0, column=2, padx=(0, 20), pady=20, sticky="nsew")
        
        self.btn = ctk.CTkButton(self, text=strings_win.BTN_RUN, height=60, command=self.run, corner_radius=12, fg_color="#2e7d32")
        self.btn.grid(row=1, column=1, columnspan=2, padx=20, pady=(0, 20), sticky="ew")

        # Перехватываем закрытие окна (крестик)
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    def fetch(self):
        d = self.sidebar.get_data()
        try:
            m = transport_win.fetch_ssh(d["host"], d["port"], d["user"], d["password"], d["path"])
            self.cfg_content = transport_win.fetch_ssh(d["host"], d["port"], d["user"], d["password"], d["path_cfg"])
            if m: 
                self.text_editor.delete("0.0", "end")
                self.text_editor.insert("end", m)
            if self.cfg_content:
                backup_win.auto_backup_if_missing(d["host"], d["port"], d["user"], d["password"], d["path_cfg"])
                self.settings_tab.update_values(self.cfg_content)
            self.run()
        except Exception as e: messagebox.showerror("SSH Error", str(e))

    def save_cfg(self):
        if not self.cfg_content: return
        if not messagebox.askyesno("Сохранение", "Записать настройки в принтер?"): return
        d, f = self.sidebar.get_data(), self.settings_tab.get_form_data()
        backup_win.create_backup_ssh(d["host"], d["port"], d["user"], d["password"], d["path_cfg"])
        text = config_win.set_cfg_value(self.cfg_content, "cs1237", "sensitivity", f["s1"])
        text = config_win.set_cfg_value(text, "cs1237", "head_block_sensitivity", f["s2"])
        text = config_win.set_cfg_value(text, "cs1237", "scratch_sensitivity", f["s3"])
        text = config_win.set_cfg_value(text, "leviQ3", "bed_temp", f["bed_t"])
        try:
            transport_win.save_ssh(d["host"], d["port"], d["user"], d["password"], d["path_cfg"], text)
            self.cfg_content = text
            messagebox.showinfo("Успех", "Настройки сохранены!")
        except Exception as e: messagebox.showerror("Ошибка", str(e))

    def run(self):
        raw = self.text_editor.get("0.0", "end").strip()
        if not raw: return
        d = self.sidebar.get_data()
        self.matrix, err = mesh_parser_win.parse_points(raw, int(d["grid_x"]), int(d["grid_y"]))
        if self.matrix is not None:
            self.analysis.update_results(self.matrix, d["grid_x"])
            map2d_win.draw_2d_map(self.t2d, self.matrix, float(d["bed_x"]), float(d["bed_y"]), int(d["grid_x"]), int(d["grid_y"]))
            save_dict = d.copy()
            save_dict.update({"z_sys": self.analysis.z_m.get(), "pitch": self.analysis.p_m.get()})
            storage_win.save_settings(save_dict)
        elif err: messagebox.showwarning("Data Error", err)

    def refresh_recs(self, _=None):
        if self.matrix is not None:
            self.analysis.update_results(self.matrix, self.sidebar.gx.get())

    def create_backup(self):
        d = self.sidebar.get_data()
        if backup_win.create_backup_ssh(d["host"], d["port"], d["user"], d["password"], d["path_cfg"]):
            messagebox.showinfo("Бэкап", "Создан успешно")

    def restore_backup(self):
        d = self.sidebar.get_data()
        if backup_win.restore_backup_ssh(d["host"], d["port"], d["user"], d["password"], d["path_cfg"]):
            self.fetch()

    def show_update_notify(self, v, data): 
        self.btn.configure(text=f"UPDATE v{v}", fg_color="#007acc")

    def on_closing(self):
        """Метод полной очистки памяти и завершения процесса"""
        try:
            plt.close('all') # Убиваем Matplotlib
            self.withdraw()  # Мгновенно скрываем окно
            # Жесткое завершение через сигнал системному ID процесса
            os.kill(os.getpid(), 9) 
        except:
            os._exit(0)

    def center_window(self):
        self.update_idletasks()
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry(f"1400x950+{int((sw-1400)/2)}+{int((sh-950)/2)}")

    def set_app_icon(self):
        try: 
            p = logic_win.resource_path("icon.ico")
            if os.path.exists(p): self.iconbitmap(p)
        except: pass

if __name__ == "__main__": App().mainloop()