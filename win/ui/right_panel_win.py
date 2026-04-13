import customtkinter as ctk
import numpy as np
from core import calculator_win
from ui.recs_win import RecCard
from utils import strings_win

class RightPanel(ctk.CTkFrame):
    def __init__(self, parent, z_sys, pitch, refresh_cb):
        # Ширина 320 — теперь стандарт для нормального отображения текста
        super().__init__(parent, width=320, fg_color="#2b2b2b", corner_radius=15)
        self.refresh_cb = refresh_cb
        self.last_matrix = None
        self.last_gx = 5
        
        self.fixed_z_sys = "Валы (2 перед, 1 зад)"
        self.fixed_pitch = 0.7 
        
        self.init_ui()

    def init_ui(self):
        # Заголовок блока анализа
        ctk.CTkLabel(self, text=strings_win.SECTION_ANALYSIS, font=("Segoe UI", 16, "bold")).pack(pady=(20, 15))
        
        # Сетка статистики (Мин, Макс и т.д.)
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

        ctk.CTkLabel(self, text="—" * 25, text_color="#3d3d3d").pack(pady=15)
        
        # Текстовые пояснения метода
        ctk.CTkLabel(self, text=strings_win.ANALYSIS_METHOD, font=("Segoe UI", 12, "bold"), text_color="#ffffff").pack(pady=2)
        ctk.CTkLabel(self, text=strings_win.ANALYSIS_SUBTEXT, font=("Segoe UI", 10), text_color="#888888").pack(pady=(0, 10))

        # Настраиваемая область со скроллом (на будущее)
        self.res_area = ctk.CTkScrollableFrame(
            self, 
            fg_color="transparent", 
            height=400,
            # Скрываем визуально ползунок, пока данных мало
            scrollbar_button_color="transparent",
            scrollbar_button_hover_color="#3d3d3d"
        )
        self.res_area.pack(fill="both", expand=True, padx=15, pady=5)

    def update_results(self, matrix, gx):
        if matrix is None: return
        self.last_matrix, self.last_gx = matrix, gx
        
        # Обновление цифровых показателей
        flat = matrix.flatten()
        self.metrics["min"].configure(text=f"{np.min(flat):.3f}")
        self.metrics["max"].configure(text=f"{np.max(flat):.3f}")
        self.metrics["range"].configure(text=f"{(np.max(flat)-np.min(flat)):.3f}")
        self.metrics["mean"].configure(text=f"{np.mean(flat):.3f}")
        self.metrics["var"].configure(text=f"{np.var(flat):.4f}")
        self.metrics["rms"].configure(text=f"{np.sqrt(np.mean(matrix**2)):.3f}")

        # Очистка старых карточек
        for w in self.res_area.winfo_children(): 
            w.destroy()
            
        # Получаем рекомендации (расчет идет от среднего)
        recs = calculator_win.get_recs(matrix, self.fixed_z_sys, self.fixed_pitch, gx)
        
        for r in recs:
            RecCard(self.res_area, r['name'], r['val'], r['turns'], r['dir'])
        
        # Логика управления скроллом: 
        # Если карточек (или других элементов в будущем) становится много — проявляем скролл
        if len(self.res_area.winfo_children()) > 4:
            self.res_area.configure(scrollbar_button_color="#3d3d3d")
        else:
            self.res_area.configure(scrollbar_button_color="transparent")