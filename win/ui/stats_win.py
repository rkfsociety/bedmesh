import customtkinter as ctk
import numpy as np

class StatsBlock(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent, fg_color="#2b2b2b", corner_radius=12)
        
        # Настройка сетки: 2 строки, 3 колонки
        self.grid_columnconfigure((0, 1, 2), weight=1)
        
        # Стили шрифтов
        self.label_font = ("Segoe UI", 12, "bold") # Увеличили с 10 до 12
        self.val_font = ("Segoe UI", 18, "bold")   # Увеличили с 14 до 18

        # Создаем ячейки
        self.min_v = self._create_stat_cell("Mesh Min", 0, 0)
        self.max_v = self._create_stat_cell("Mesh Max", 0, 1)
        self.rng_v = self._create_stat_cell("Mesh Range", 0, 2)
        
        self.var_v = self._create_stat_cell("Mesh Variance", 1, 0)
        self.mean_v = self._create_stat_cell("Mesh Mean", 1, 1)
        self.rms_v = self._create_stat_cell("Mesh RMS", 1, 2)

    def _create_stat_cell(self, title, row, col):
        frame = ctk.CTkFrame(self, fg_color="#333333", corner_radius=8)
        frame.grid(row=row, column=col, padx=5, pady=5, sticky="nsew")
        
        ctk.CTkLabel(frame, text=title, font=self.label_font, text_color="#aaaaaa").pack(pady=(10, 2))
        val_lbl = ctk.CTkLabel(frame, text="0.000", font=self.val_font, text_color="white")
        val_lbl.pack(pady=(2, 10))
        return val_lbl

    def update_stats(self, stats):
        self.min_v.configure(text=f"{stats['min']:.3f}")
        self.max_v.configure(text=f"{stats['max']:.3f}")
        self.rng_v.configure(text=f"{stats['range']:.3f}")
        self.var_v.configure(text=f"{stats['variance']:.4f}")
        self.mean_v.configure(text=f"{stats['mean']:.3f}")
        self.rms_v.configure(text=f"{stats['rms']:.3f}")

def get_mesh_stats(matrix):
    """Расчет статистики матрицы"""
    return {
        'min': np.min(matrix),
        'max': np.max(matrix),
        'range': np.max(matrix) - np.min(matrix),
        'variance': np.var(matrix),
        'mean': np.mean(matrix),
        'rms': np.sqrt(np.mean(matrix**2))
    }