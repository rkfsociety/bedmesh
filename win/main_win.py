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
        # 1. Сначала настраиваем окно
        self.center_window()
        self.title(f"{strings_win.APP_TITLE} v{logic_win.VERSION}")
        self.set_app_icon()
        
        # 2. Инициализируем данные
        self.matrix, self.cfg_content = None, ""
        self.last_raw_data = ""
        self.settings = storage_win.load_settings()
        
        # 3. Настраиваем сетку
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        # 4. РИСУЕМ ИНТЕРФЕЙС (Теперь все методы ниже будут доступны)
        self.init_ui()
        
        # 5. Проверка обновлений
        updater_win.check_for_updates(logic_win.VERSION, self.show_update_notify)

    def init_ui(self):
        # Контейнер сайдбара
        self.sb_cont = ctk.CTkFrame(self, width=360, corner_radius=0, fg_color="#2b2b2b")
        self.sb_cont.grid(row=0, column=0, rowspan=2, sticky="nsew")
        self.sb_cont.grid_propagate(False)

        # Сайдбар
        self.sidebar = Sidebar(self.sb_cont, self.settings, self.fetch, self.toggle_log_view)
        self.sidebar.pack(fill="both", expand=True)

        # Табы
        self.tabs = ctk.CTkTabview(self, corner_radius=15)
        self.tabs.grid(row=0, column=1, padx=20, pady=20, sticky="nsew")
        self.t2d = self.tabs.add(strings_win.TAB_2D)
        self.tset_frame = self.tabs.add("ПАРАМЕТРЫ")
        self.traw_tab = None

        # Вкладка настроек
        self.settings_tab = SettingsTab(self.tset_frame, self.create_backup, self.restore_backup, self.save_cfg)
        self.settings_tab.pack(fill="both", expand=True)

        # Анализ
        default_z = self.settings.get("z_sys", strings_win.Z_SYSTEMS[0])
        self.analysis = AnalysisPanel(self, default_z, self.settings.get("pitch", "0.7"), self.refresh_recs)
        self.analysis.grid(row=0, column=2, padx=(0, 20), pady=20, sticky="nsew")
        
        # Кнопка запуска
        self.btn = ctk.CTkButton(self, text=strings_win.BTN_RUN, height=60, command=self.run, corner_radius=12, fg_color="#2e7d32")
        self.btn.grid(row=1, column=1, columnspan=2, padx=20, pady=(0, 20), sticky="ew")

        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    def toggle_log_view(self, state):
        if state == 1:
            if strings_win.TAB_RAW not in self.tabs._tab_dict:
                self.traw_tab = self.tabs.add(strings_win.TAB_RAW)
                self.text_editor = ctk.CTkTextbox(self.traw_tab, font=("Consolas", 12))
                self.text_editor.pack(fill="both", expand=True)
                if self.last_raw_data: self.text_editor.insert("end", self.last_raw_data)
        else:
            if strings_win.TAB_RAW in self.tabs._tab_dict:
                self.tabs.delete(strings_win.TAB_RAW)
                self.traw_tab = None

    def fetch(self):
        d = self.sidebar.get_data()
        try:
            m = transport_win.fetch_ssh(d["host"], d["port"], d["user"], d["password"], d["path"])
            self.cfg_content = transport_win.fetch_ssh(d["host"], d["port"], d["user"], d["password"], d["path_cfg"])
            if m:
                self.last_raw_data = m
                if self.traw_tab:
                    self.text_editor.delete("0.0", "end")
                    self.text_editor.insert("end", m)
            if self.cfg_content:
                backup_win.auto_backup_if_missing(d["host"], d["port"], d["user"], d["password"], d["path_cfg"])
                self.settings_tab.update_values(self.cfg_content)
            self.run()
        except Exception as e: messagebox.showerror("SSH Error", str(e))

    def save_cfg(self):
        if not self.cfg_content: return
        if not messagebox.askyesno("Сохранение", "Записать конфиг в принтер?"): return
        d, f = self.sidebar.get_data(), self.settings_tab.get_form_data()
        backup_win.create_backup_ssh(d["host"], d["port"], d["user"], d["password"], d["path_cfg"])
        text = config_win.set_cfg_value(self.cfg_content, "cs1237", "sensitivity", f["s1"])
        text = config_win.set_cfg_value(text, "cs1237", "head_block_sensitivity", f["s2"])
        text = config_win.set_cfg_value(text, "cs1237", "scratch_sensitivity", f["s3"])
        text = config_win.set_cfg_value(text, "leviQ3", "bed_temp", f["bed_t"])
        try:
            transport_win.save_ssh(d["host"], d["port"], d["user"], d["password"], d["path_cfg"], text)
            self.cfg_content = text; messagebox.showinfo("Успех", "Настройки сохранены")
        except Exception as e: messagebox.showerror("Ошибка", str(e))

    def run(self):
        raw = self.text_editor.get("0.0", "end").strip() if self.traw_tab else self.last_raw_data.strip()
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
        if self.matrix is not None: self.analysis.update_results(self.matrix, self.sidebar.gx.get())

    def create_backup(self):
        d = self.sidebar.get_data()
        if backup_win.create_backup_ssh(d["host"], d["port"], d["user"], d["password"], d["path_cfg"]):
            messagebox.showinfo("Бэкап", "Создан успешно")

    def restore_backup(self):
        d = self.sidebar.get_data()
        if backup_win.restore_backup_ssh(d["host"], d["port"], d["user"], d["password"], d["path_cfg"]): self.fetch()

    def show_update_notify(self, v, data): self.btn.configure(text=f"UPDATE v{v}", fg_color="#007acc")

    def on_closing(self):
        try:
            plt.close('all'); self.withdraw()
            os.kill(os.getpid(), 9)
        except: os._exit(0)

    def center_window(self):
        self.update_idletasks()
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        w, h = int(sw * 0.8), int(sh * 0.8)
        self.geometry(f"{w}x{h}+{int((sw-w)/2)}+{int((sh-h)/2)}")

    def set_app_icon(self):
        try: 
            p = logic_win.resource_path("icon.ico")
            if os.path.exists(p): self.iconbitmap(p)
        except: pass

if __name__ == "__main__": App().mainloop()