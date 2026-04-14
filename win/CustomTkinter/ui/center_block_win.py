import customtkinter as ctk
from ui import map2d_win
from utils import strings_win, styles_win

class CenterBlock(ctk.CTkTabview):
    def __init__(self, parent):
        super().__init__(parent, fg_color="#2b2b2b")
        self.add(strings_win.TAB_2D)
        self.map2d = map2d_win.MapCanvas(self.tab(strings_win.TAB_2D))
        self.map2d.pack(fill="both", expand=True, padx=5, pady=5)
        self.raw_tab_exists = False
        self.config_tab_exists = False
        self.entries_config = {} 

    def show_raw_tab(self):
        if not self.raw_tab_exists:
            name = strings_win.TAB_RAW
            self.add(name)
            self.text_mutable = ctk.CTkTextbox(self.tab(name), font=("Consolas", 12))
            self.text_mutable.pack(fill="both", expand=True, padx=10, pady=10)
            self.raw_tab_exists = True

    def hide_raw_tab(self):
        if self.raw_tab_exists:
            self.delete(strings_win.TAB_RAW)
            self.raw_tab_exists = False

    def show_config_editor_tab(self, save_callback, restore_callback):
        if not self.config_tab_exists:
            name = "Настройка Принтера"
            self.add(name)
            main_frame = ctk.CTkFrame(self.tab(name), fg_color="transparent")
            main_frame.pack(fill="both", expand=True, padx=10, pady=10)
            left_col = ctk.CTkScrollableFrame(main_frame, fg_color="#242424", label_text="РЕДАКТОР КОНФИГУРАЦИИ")
            left_col.pack(side="left", fill="both", expand=True, padx=(0, 5))

            self._create_header(left_col, "🌐 ПАРАМЕТРЫ СЕТКИ (BED MESH)")
            self.entries_config["mesh_min"] = self._create_row(left_col, "mesh_min")
            self.entries_config["mesh_max"] = self._create_row(left_col, "mesh_max")
            self.entries_config["probe_count"] = self._create_row(left_col, "probe_count")
            ctk.CTkLabel(left_col, text="", height=10).pack()

            self._create_header(left_col, "🚀 УСКОРЕНИЕ ACE PRO")
            self.entries_config["ace_feed"] = self._create_row(left_col, "v2_feed_speed")
            self.entries_config["ace_unwind"] = self._create_row(left_col, "v2_unwind_speed")

            right_col = ctk.CTkFrame(main_frame, fg_color="#242424", width=300)
            right_col.pack(side="right", fill="y", padx=(5, 0))
            right_col.pack_propagate(False)

            ctk.CTkLabel(right_col, text="УПРАВЛЕНИЕ", font=styles_win.FONTS["ui_bold"]).pack(pady=10)
            btn_save = ctk.CTkButton(right_col, text="💾 СОХРАНИТЬ", fg_color="#28a745", hover_color="#218838", command=save_callback, height=45)
            btn_save.pack(fill="x", padx=15, pady=10)
            ctk.CTkLabel(right_col, text="—" * 15, text_color="#3d3d3d").pack()
            ctk.CTkLabel(right_col, text="ИСТОРИЯ (БЭКАПЫ):", font=("Segoe UI", 11)).pack(pady=(10, 0))
            self.backup_var = ctk.StringVar(value="Нет данных")
            self.backup_menu = ctk.CTkOptionMenu(right_col, values=["Нет данных"], variable=self.backup_var, fg_color="#3d3d3d")
            self.backup_menu.pack(fill="x", padx=15, pady=5)
            btn_restore = ctk.CTkButton(right_col, text="⏪ ВОССТАНОВИТЬ", fg_color="#a83232", hover_color="#7a2424", command=lambda: restore_callback(self.backup_var.get()))
            btn_restore.pack(fill="x", padx=15, pady=10)
            self.config_tab_exists = True

    def _create_header(self, master, text):
        f = ctk.CTkFrame(master, fg_color="#333333", height=30)
        f.pack(fill="x", pady=(10, 5), padx=5)
        ctk.CTkLabel(f, text=text, font=("Segoe UI", 11, "bold")).pack(side="left", padx=10)

    def _create_row(self, master, label):
        f = ctk.CTkFrame(master, fg_color="transparent")
        f.pack(fill="x", pady=2)
        ctk.CTkLabel(f, text=label, width=140, anchor="w").pack(side="left")
        e = ctk.CTkEntry(f, fg_color="#1d1d1d")
        e.pack(side="right", fill="x", expand=True, padx=5)
        return e

    def get_all_fields(self):
        return {k: v.get() for k, v in self.entries_config.items()}

    def fill_config_fields(self, data):
        if not self.config_tab_exists: return
        for k, v in data.items():
            if k in self.entries_config:
                self.entries_config[k].delete(0, "end")
                self.entries_config[k].insert(0, str(v))

    def update_backup_list(self, backups):
        if self.config_tab_exists and backups:
            formatted = backups[::-1]
            self.backup_menu.configure(values=formatted)
            self.backup_var.set(formatted[0])

    def update_display(self, matrix, gx, raw_mutable):
        if matrix is not None: self.map2d.draw(matrix, gx)
        if raw_mutable and hasattr(self, 'text_mutable') and self.text_mutable:
            self.text_mutable.delete("1.0", "end")
            self.text_mutable.insert("end", raw_mutable)

    def hide_config_editor_tab(self):
        if self.config_tab_exists:
            self.delete("Настройка Принтера")
            self.config_tab_exists = False