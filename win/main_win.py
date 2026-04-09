import customtkinter as ctk
import logic_win, styles_win, ui_elements_win, strings_win, updater_win, viz_win, backup_win
import matplotlib.pyplot as plt
import sys, os, ctypes
from tkinter import messagebox

try: ctypes.windll.shcore.SetProcessDpiAwareness(1)
except: pass

ctk.set_appearance_mode("dark")

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.width, self.height = 1350, 900
        self.title(f"{strings_win.APP_TITLE} v{logic_win.VERSION}")
        self.center_window()
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.matrix, self.recs_data, self.update_data = None, [], None
        self.cfg_content = ""
        self.settings = logic_win.load_settings()

        self.grid_columnconfigure(1, weight=1); self.grid_rowconfigure(0, weight=1)

        # --- SIDEBAR ---
        self.sidebar = ctk.CTkFrame(self, width=300, corner_radius=0); self.sidebar.grid(row=0, column=0, rowspan=2, sticky="nsew")
        ctk.CTkLabel(self.sidebar, text=strings_win.SECTION_SSH, font=styles_win.FONTS["title"]).pack(pady=(15, 5))
        self.ip = ui_elements_win.LabeledEntry(self.sidebar, strings_win.LBL_IP, self.settings.get("host", ""))
        self.port = ui_elements_win.LabeledEntry(self.sidebar, strings_win.LBL_PORT, self.settings.get("port", "22"))
        self.user = ui_elements_win.LabeledEntry(self.sidebar, strings_win.LBL_USER, self.settings.get("user", "pi"))
        self.pwd = ui_elements_win.LabeledEntry(self.sidebar, strings_win.LBL_PASS, self.settings.get("password", ""), show="*")
        self.path_mesh = ui_elements_win.LabeledEntry(self.sidebar, strings_win.LBL_PATH, self.settings.get("path", ""))
        self.path_cfg = ui_elements_win.LabeledEntry(self.sidebar, strings_win.LBL_PATH_CFG, self.settings.get("path_cfg", ""))
        ctk.CTkButton(self.sidebar, text=strings_win.BTN_FETCH, command=self.fetch, fg_color="#3d3d3d").pack(pady=10, padx=20, fill="x")
        
        ctk.CTkLabel(self.sidebar, text=strings_win.SECTION_GEOMETRY, font=styles_win.FONTS["ui_bold"]).pack(pady=(10, 5))
        self.bx = ui_elements_win.LabeledEntry(self.sidebar, strings_win.LBL_BED_X, self.settings.get("bed_x", "250"))
        self.by = ui_elements_win.LabeledEntry(self.sidebar, strings_win.LBL_BED_Y, self.settings.get("bed_y", "250"))
        self.gx = ui_elements_win.LabeledEntry(self.sidebar, strings_win.LBL_GRID_X, self.settings.get("grid_x", "5"))
        self.gy = ui_elements_win.LabeledEntry(self.sidebar, strings_win.LBL_GRID_Y, self.settings.get("grid_y", "5"))
        ctk.CTkButton(self.sidebar, text="🔄 СИНХРОНИЗИРОВАТЬ ГЕОМЕТРИЮ", font=styles_win.FONTS["micro"], command=self.sync_geometry, fg_color="#444444").pack(pady=5, padx=20, fill="x")

        # --- TABS ---
        self.tabs = ctk.CTkTabview(self, corner_radius=15); self.tabs.grid(row=0, column=1, padx=20, pady=20, sticky="nsew")
        self.t2d, self.traw, self.tsettings = self.tabs.add(strings_win.TAB_2D), self.tabs.add(strings_win.TAB_RAW), self.tabs.add("ПАРАМЕТРЫ PRINTER.CFG")
        self.text_editor = ctk.CTkTextbox(self.traw, font=styles_win.FONTS["code"]); self.text_editor.pack(fill="both", expand=True)
        
        # Контент вкладки параметров
        self.cfg_frame = ctk.CTkScrollableFrame(self.tsettings, fg_color="transparent"); self.cfg_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Фрейм бэкапа
        self.bf = ctk.CTkFrame(self.cfg_frame, fg_color="#2b2b2b", corner_radius=10); self.bf.pack(fill="x", pady=10, padx=10)
        ctk.CTkLabel(self.bf, text="РЕЗЕРВНОЕ КОПИРОВАНИЕ", font=styles_win.FONTS["micro"]).pack(pady=5)
        bg = ctk.CTkFrame(self.bf, fg_color="transparent"); bg.pack(fill="x", pady=5, padx=10)
        ctk.CTkButton(bg, text="СОЗДАТЬ БЭКАП (.bak)", fg_color="#444444", command=self.create_backup).pack(side="left", expand=True, padx=5, pady=5)
        ctk.CTkButton(bg, text="ВОССТАНОВИТЬ ИЗ БЭКАПА", fg_color="#554444", command=self.restore_backup).pack(side="left", expand=True, padx=5, pady=5)

        ctk.CTkLabel(self.cfg_frame, text="Чувствительность тензодатчика [cs1237]", font=styles_win.FONTS["ui_bold"]).pack(pady=(20, 10))
        self.s1 = ui_elements_win.LabeledEntry(self.cfg_frame, "sensitivity", "")
        self.s2 = ui_elements_win.LabeledEntry(self.cfg_frame, "head_block_sensitivity", "")
        self.s3 = ui_elements_win.LabeledEntry(self.cfg_frame, "scratch_sensitivity", "")
        
        self.save_btn = ctk.CTkButton(self.tsettings, text="💾 СОХРАНИТЬ В ПРИНТЕР", height=50, fg_color=styles_win.COLORS["dark"]["error"], command=self.save_cfg)
        self.save_btn.pack(pady=20, padx=20, fill="x")

        # --- RIGHT PANEL ---
        self.right = ctk.CTkFrame(self, width=340); self.right.grid(row=0, column=2, padx=(0, 20), pady=20, sticky="nsew"); self.right.pack_propagate(False)
        ctk.CTkLabel(self.right, text=strings_win.SECTION_ALIGN, font=styles_win.FONTS["ui_bold"]).pack(pady=15)
        self.z_m = ctk.CTkOptionMenu(self.right, values=strings_win.Z_SYSTEMS, command=self.refresh_recs); self.z_m.set(self.settings.get("z_sys", strings_win.Z_SYSTEMS[0])); self.z_m.pack(pady=10, padx=20, fill="x")
        self.p_l = ctk.CTkLabel(self.right, text=strings_win.LBL_PITCH); self.p_l.pack(); self.p_m = ctk.CTkOptionMenu(self.right, values=["0.7", "0.5", "0.8"], command=self.refresh_recs); self.p_m.set(self.settings.get("pitch", "0.7")); self.p_m.pack(pady=5, padx=20, fill="x")
        ctk.CTkButton(self.right, text="📋 КОПИРОВАТЬ ОТЧЕТ", font=styles_win.FONTS["micro"], height=30, fg_color="#333333", command=self.copy_to_clipboard).pack(pady=10, padx=20, fill="x")
        self.rec_s = ctk.CTkScrollableFrame(self.right, fg_color="transparent"); self.rec_s.pack(fill="both", expand=True, padx=5, pady=10)
        self.empty = ctk.CTkLabel(self.rec_s, text=strings_win.MSG_WAITING, font=(styles_win.FONT_NAME, 10), text_color="#555555"); self.empty.pack(pady=50)

        self.btn = ctk.CTkButton(self, text=strings_win.BTN_RUN, height=60, fg_color=styles_win.COLORS["dark"]["success"], font=styles_win.FONTS["title"], command=self.on_click, corner_radius=12)
        self.btn.grid(row=1, column=1, columnspan=2, padx=20, pady=(0, 20), sticky="ew")
        updater_win.check_for_updates(logic_win.VERSION, self.show_update_notify)

    def center_window(self):
        self.update_idletasks(); sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        x, y = int((sw / 2) - (self.width / 2)), int((sh / 2) - (self.height / 2))
        self.geometry(f"{self.width}x{self.height}+{x}+{y}")

    def create_backup(self):
        if backup_win.create_backup_ssh(self.ip.get(), self.port.get(), self.user.get(), self.pwd.get(), self.path_cfg.get()):
            messagebox.showinfo("Бэкап", "Успешно создан .bak файл")
        else: messagebox.showerror("Ошибка", "Не удалось создать бэкап")

    def restore_backup(self):
        if not messagebox.askyesno("Восстановление", "Заменить printer.cfg бэкапом?"): return
        if backup_win.restore_backup_ssh(self.ip.get(), self.port.get(), self.user.get(), self.pwd.get(), self.path_cfg.get()):
            messagebox.showinfo("Успех", "Конфиг восстановлен. Перезагрузите принтер."); self.fetch()
        else: messagebox.showerror("Ошибка", "Файл бэкапа не найден")

    def save_cfg(self):
        if not self.cfg_content: return
        if not messagebox.askyesno("Сохранение", "Сделать бэкап и сохранить?"): return
        backup_win.create_backup_ssh(self.ip.get(), self.port.get(), self.user.get(), self.pwd.get(), self.path_cfg.get())
        new = logic_win.set_cfg_value(self.cfg_content, "cs1237", "sensitivity", self.s1.get())
        new = logic_win.set_cfg_value(new, "cs1237", "head_block_sensitivity", self.s2.get())
        new = logic_win.set_cfg_value(new, "cs1237", "scratch_sensitivity", self.s3.get())
        try:
            logic_win.save_ssh(self.ip.get(), self.port.get(), self.user.get(), self.pwd.get(), self.path_cfg.get(), new)
            self.cfg_content = new; messagebox.showinfo("Успех", "Сохранено!")
        except Exception as e: messagebox.showerror("Ошибка", str(e))

    def sync_geometry(self):
        if not self.cfg_content: return
        px, py, pc = logic_win.get_cfg_value(self.cfg_content, "stepper_x", "position_max"), logic_win.get_cfg_value(self.cfg_content, "stepper_y", "position_max"), logic_win.get_cfg_value(self.cfg_content, "bed_mesh", "probe_count")
        if px: self.bx.entry.delete(0, 'end'); self.bx.entry.insert(0, px)
        if py: self.by.entry.delete(0, 'end'); self.by.entry.insert(0, py)
        if pc:
            try: gx, gy = pc.split(','); self.gx.entry.delete(0, 'end'); self.gx.entry.insert(0, gx.strip()); self.gy.entry.delete(0, 'end'); self.gy.entry.insert(0, gy.strip())
            except: pass
        messagebox.showinfo("Ок", "Данные синхронизированы")

    def show_update_notify(self, v, data): self.update_data = data; self.btn.configure(text=f"UPDATE v{v}", fg_color="#007acc")
    def copy_to_clipboard(self):
        if not self.recs_data: return
        r = "--- Bed Mesh Report ---\n" + "\n".join([f"{i['name']}: {i['val']:.3f} mm ({i['turns']}) -> {i['dir']}" for i in self.recs_data])
        self.clipboard_clear(); self.clipboard_append(r); messagebox.showinfo("Ок", "Скопировано")
    def on_click(self):
        if self.update_data: updater_win.install_update(self.update_data)
        else: self.run()
    def fetch(self):
        try:
            m = logic_win.fetch_ssh(self.ip.get(), self.port.get(), self.user.get(), self.pwd.get(), self.path_mesh.get())
            self.cfg_content = logic_win.fetch_ssh(self.ip.get(), self.port.get(), self.user.get(), self.pwd.get(), self.path_cfg.get())
            if m: self.text_editor.delete("0.0", "end"); self.text_editor.insert("end", m)
            if self.cfg_content:
                self.s1.entry.delete(0, 'end'); self.s1.entry.insert(0, logic_win.get_cfg_value(self.cfg_content, "cs1237", "sensitivity"))
                self.s2.entry.delete(0, 'end'); self.s2.entry.insert(0, logic_win.get_cfg_value(self.cfg_content, "cs1237", "head_block_sensitivity"))
                self.s3.entry.delete(0, 'end'); self.s3.entry.insert(0, logic_win.get_cfg_value(self.cfg_content, "cs1237", "scratch_sensitivity"))
            self.run()
        except Exception as e: messagebox.showerror("SSH Error", str(e))
    def refresh_recs(self, _=None):
        if self.matrix is not None:
            self.recs_data, is_s = logic_win.get_recs(self.matrix, self.z_m.get(), float(self.p_m.get()), int(self.gx.get()))
            for w in self.rec_s.winfo_children(): w.destroy()
            for i in self.recs_data: ui_elements_win.RecCard(self.rec_s, i['name'], i['val'], i['turns'], i['dir'])
            if is_s: self.p_l.pack(); self.p_m.pack(pady=5, padx=20, fill="x")
            else: self.p_l.pack_forget(); self.p_m.pack_forget()
    def run(self):
        try:
            raw = self.text_editor.get("0.0", "end").strip()
            if not raw: return
            gx, gy = int(self.gx.get()), int(self.gy.get())
            self.matrix, err = logic_win.parse_points(raw, gx, gy)
            if self.matrix is not None:
                self.refresh_recs(); viz_win.draw_2d_map(self.t2d, self.matrix, float(self.bx.get()), float(self.by.get()), gx, gy)
                logic_win.save_settings({"host": self.ip.get(), "port": self.port.get(), "user": self.user.get(), "password": self.pwd.get(), "path": self.path_mesh.get(), "path_cfg": self.path_cfg.get(), "bed_x": self.bx.get(), "bed_y": self.by.get(), "grid_x": self.gx.get(), "grid_y": self.gy.get(), "z_sys": self.z_m.get(), "pitch": self.p_m.get()})
            else: messagebox.showwarning("Data Error", err)
        except Exception as e: messagebox.showerror("Error", str(e))
    def on_closing(self): plt.close('all'); self.destroy(); sys.exit(0)

if __name__ == "__main__": App().mainloop()