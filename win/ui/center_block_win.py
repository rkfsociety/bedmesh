import customtkinter as ctk
from ui import map2d_win
from utils import strings_win, styles_win

class CenterBlock(ctk.CTkTabview):
    def __init__(self, parent):
        super().__init__(parent, fg_color="#2b2b2b")
        
        # Основная вкладка 2D карты
        self.add(strings_win.TAB_2D)
        # Устанавливаем холст для карты и заставляем его растягиваться (fill="both", expand=True)
        self.map2d = map2d_win.MapCanvas(self.tab(strings_win.TAB_2D))
        self.map2d.pack(fill="both", expand=True, padx=5, pady=5)

        self.raw_tab_exists = False
        self.config_tab_exists = False
        self.entries_config = {}

    def show_raw_tab(self):
        """Создание вкладки с сырым JSON данными"""
        if not self.raw_tab_exists:
            name = strings_win.TAB_RAW
            self.add(name)
            # Текстовое поле теперь занимает всё пространство вкладки
            self.text_mutable = ctk.CTkTextbox(self.tab(name), font=("Consolas", 12))
            self.text_mutable.pack(fill="both", expand=True, padx=10, pady=10)
            self.raw_tab_exists = True

    def hide_raw_tab(self):
        """Удаление вкладки сырых данных"""
        if self.raw_tab_exists:
            self.delete(strings_win.TAB_RAW)
            self.raw_tab_exists = False

    def show_config_editor_tab(self, save_callback, restore_callback):
        """Создание вкладки редактора конфигурации принтера"""
        if not self.config_tab_exists:
            name = "Настройка Принтера"
            self.add(name)
            
            # Главный контейнер для редактора
            main_frame = ctk.CTkFrame(self.tab(name), fg_color="transparent")
            main_frame.pack(fill="both", expand=True, padx=10, pady=10)

            # Левая колонка с параметрами (скролл-зона) - растягивается максимально
            left_col = ctk.CTkScrollableFrame(main_frame, fg_color="#242424", label_text="ПАРАМЕТРЫ")
            left_col.pack(side="left", fill="both", expand=True, padx=(0, 5))

            ctk.CTkLabel(left_col, text="[stepper_z]", font=styles_win.FONTS["ui_bold"]).pack(anchor="w")
            self.entries_config["stepper_z_rd"] = self._create_row(left_col, "rotation_distance")
            
            ctk.CTkLabel(left_col, text="\n[probe]", font=styles_win.FONTS["ui_bold"]).pack(anchor="w")
            self.entries_config["probe_z_offset"] = self._create_row(left_col, "z_offset")
            
            ctk.CTkLabel(left_col, text="\n[bed_mesh]", font=styles_win.FONTS["ui_bold"]).pack(anchor="w")
            self.entries_config["mesh_min"] = self._create_row(left_col, "mesh_min")
            self.entries_config["mesh_max"] = self._create_row(left_col, "mesh_max")

            # Правая колонка с кнопками управления - фиксированная ширина 300
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

    def _create_row(self, master, label):
        """Вспомогательный метод для создания строки ввода в редакторе"""
        f = ctk.CTkFrame(master, fg_color="transparent")
        f.pack(fill="x", pady=2)
        ctk.CTkLabel(f, text=label, width=130, anchor="w").pack(side="left")
        e = ctk.CTkEntry(f, fg_color="#1d1d1d")
        e.pack(side="right", fill="x", expand=True, padx=5)
        return e

    def update_backup_list(self, backups):
        """Обновление выпадающего списка бэкапов"""
        if self.config_tab_exists and backups:
            formatted = backups[::-1]
            self.backup_menu.configure(values=formatted)
            self.backup_var.set(formatted[0])

    def fill_config_fields(self, data):
        """Заполнение полей редактора данными из конфига"""
        if not self.config_tab_exists: return
        for k, v in data.items():
            if k in self.entries_config:
                self.entries_config[k].delete(0, "end")
                self.entries_config[k].insert(0, str(v))

    def update_display(self, matrix, gx, raw_mutable):
        """Синхронное обновление графики и текстового лога"""
        if matrix is not None:
            self.map2d.draw(matrix, gx)
        if raw_mutable and hasattr(self, 'text_mutable') and self.text_mutable:
            self.text_mutable.delete("1.0", "end")
            self.text_mutable.insert("end", raw_mutable)

    def hide_config_editor_tab(self):
        """Скрытие вкладки редактора"""
        if self.config_tab_exists:
            self.delete("Настройка Принтера")
            self.config_tab_exists = False