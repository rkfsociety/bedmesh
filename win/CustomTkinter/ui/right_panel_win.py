import customtkinter as ctk
import numpy as np
from core import calculator_win
from ui.recs_win import RecCard
from utils import strings_win, logic_win

class RightPanel(ctk.CTkFrame):
    def __init__(self, parent, z_sys, pitch, refresh_cb):
        # Фиксированная ширина 380 для симметрии
        super().__init__(parent, width=380, fg_color="#2b2b2b", corner_radius=15)
        self.refresh_cb = refresh_cb
        self.last_matrix = None
        self.last_gx = 5
        self.fixed_z_sys = "Валы (2 перед, 1 зад)"
        self.fixed_pitch = 0.7 
        self.init_ui()

    def init_ui(self):
        # --- Блок статистики (Анализ меша) ---
        ctk.CTkLabel(self, text=strings_win.SECTION_ANALYSIS, font=("Segoe UI", 16, "bold")).pack(pady=(20, 15))
        
        self.f_stats = ctk.CTkFrame(self, fg_color="transparent")
        self.f_stats.pack(fill="x", padx=15)
        self.metrics = {}
        
        labels = [
            (strings_win.METRIC_MIN, "min"), (strings_win.METRIC_MAX, "max"), 
            (strings_win.METRIC_RANGE, "range"), (strings_win.METRIC_MEAN, "mean"), 
            (strings_win.METRIC_VAR, "var"), (strings_win.METRIC_RMS, "rms")
        ]
        
        for i, (name, key) in enumerate(labels):
            row, col = divmod(i, 2)
            f = ctk.CTkFrame(self.f_stats, fg_color="#333333", corner_radius=8)
            f.grid(row=row, column=col, padx=5, pady=5, sticky="nsew")
            ctk.CTkLabel(f, text=name, font=("Segoe UI", 11), text_color="#aaaaaa").pack(pady=(2, 0))
            self.metrics[key] = ctk.CTkLabel(f, text="0.000", font=("Segoe UI", 13, "bold"), text_color="#00ffcc")
            self.metrics[key].pack(pady=(0, 2))
            self.f_stats.grid_columnconfigure(col, weight=1)

        ctk.CTkLabel(self, text="—" * 30, text_color="#3d3d3d").pack(pady=10)
        
        # --- Блок рекомендаций (Коррекция) ---
        ctk.CTkLabel(self, text=strings_win.ANALYSIS_METHOD, font=("Segoe UI", 14, "bold"), text_color="#ffffff").pack(pady=2)
        ctk.CTkLabel(self, text="(минимизирует кручение валов)", font=("Segoe UI", 10), text_color="#888888").pack(pady=(0, 10))

        # ФИКС: Заменяем ScrollableFrame на обычный Frame
        self.res_area = ctk.CTkFrame(self, fg_color="transparent")
        self.res_area.pack(fill="x", padx=15, pady=5)

        # Располагаем инфо-блок в самом низу
        self.f_info = ctk.CTkFrame(self, fg_color="#1e1e1e", corner_radius=12, border_width=1, border_color="#3d3d3d")
        self.f_info.pack(side="bottom", fill="x", padx=15, pady=15)

        self.conn_frame = ctk.CTkFrame(self.f_info, fg_color="transparent")
        self.conn_frame.pack(fill="x", padx=15, pady=(12, 6))
        ctk.CTkLabel(self.conn_frame, text="Статус:", font=("Segoe UI", 13, "bold"), text_color="#ffffff").pack(side="left")
        self.lbl_status = ctk.CTkLabel(self.conn_frame, text="Готов к работе", font=("Segoe UI", 14, "bold"), text_color="#00ffcc")
        self.lbl_status.pack(side="right")

        ctk.CTkFrame(self.f_info, fg_color="#3d3d3d", height=1).pack(fill="x", padx=10)

        self.ver_frame = ctk.CTkFrame(self.f_info, fg_color="transparent")
        self.ver_frame.pack(fill="x", padx=15, pady=(6, 12))
        ctk.CTkLabel(self.ver_frame, text="Версия:", font=("Segoe UI", 12), text_color="#cccccc").pack(side="left")
        self.lbl_ver_val = ctk.CTkLabel(self.ver_frame, text=f"{logic_win.VERSION}", font=("Segoe UI", 12, "bold"), text_color="#ffffff")
        self.lbl_ver_val.pack(side="left", padx=5)
        self.lbl_upd = ctk.CTkLabel(self.ver_frame, text="Актуальна", font=("Segoe UI", 12, "bold"), text_color="#4dff88", cursor="hand2")
        self.lbl_upd.pack(side="right")

    def set_status(self, mode="ready"):
        if mode == "busy":
            self.lbl_status.configure(text="Подключение...", text_color="#ffcc00")
        elif mode == "error":
            self.lbl_status.configure(text="Ошибка связи", text_color="#ff4d4d")
        else:
            self.lbl_status.configure(text="Готов к работе", text_color="#00ffcc")

    def show_update_available(self, callback):
        self.lbl_upd.configure(text="Обновление!", text_color="#ff4d4d", font=("Segoe UI", 12, "bold", "underline"))
        self.lbl_upd.bind("<Button-1>", lambda e: callback())

    def update_results(self, matrix, gx):
        if matrix is None: return
        self.last_matrix, self.last_gx = matrix, gx
        
        # Обновляем цифры статистики
        flat = matrix.flatten()
        self.metrics["min"].configure(text=f"{np.min(flat):.3f}")
        self.metrics["max"].configure(text=f"{np.max(flat):.3f}")
        self.metrics["range"].configure(text=f"{(np.max(flat)-np.min(flat)):.3f}")
        self.metrics["mean"].configure(text=f"{np.mean(flat):.3f}")
        self.metrics["var"].configure(text=f"{np.var(flat):.4f}")
        self.metrics["rms"].configure(text=f"{np.sqrt(np.mean(matrix**2)):.3f}")

        # Очищаем старые рекомендации
        for w in self.res_area.winfo_children(): 
            w.destroy()
            
        # Генерируем новые карточки
        recs = calculator_win.get_recs(matrix, self.fixed_z_sys, self.fixed_pitch, gx)
        
        for r in recs:
            # Карточки будут просто паковаться одна под другой в обычном фрейме
            RecCard(self.res_area, r['name'], r['val'], r['turns'], r['dir'])