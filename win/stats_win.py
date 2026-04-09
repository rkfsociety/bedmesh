import customtkinter as ctk
import numpy as np
import styles_win

def get_mesh_stats(matrix):
    """Математический расчет показателей карты высот"""
    if matrix is None: return None
    flat = matrix.flatten()
    return {
        "min": np.min(flat),
        "max": np.max(flat),
        "range": np.max(flat) - np.min(flat),
        "variance": np.var(flat),
        "mean": np.mean(flat),
        "rms": np.sqrt(np.mean(flat**2))
    }

class StatsBlock(ctk.CTkFrame):
    """Информационный блок статистики 3x2"""
    def __init__(self, master):
        super().__init__(master, fg_color="#222222", corner_radius=12, border_width=1, border_color="#333333")
        self.labels = {}
        fields = [
            ("Mesh Min", "min"), ("Mesh Max", "max"), ("Mesh Range", "range"),
            ("Mesh Variance", "var"), ("Mesh Mean", "mean"), ("Mesh RMS", "rms")
        ]
        
        for i, (name, key) in enumerate(fields):
            row, col = divmod(i, 3)
            cell = ctk.CTkFrame(self, fg_color="#2b2b2b", corner_radius=8)
            cell.grid(row=row, column=col, padx=5, pady=5, sticky="nsew")
            
            ctk.CTkLabel(cell, text=name, font=(styles_win.FONT_NAME, 9), text_color="#999999").pack(pady=(5, 0))
            lbl = ctk.CTkLabel(cell, text="---", font=(styles_win.FONT_NAME, 12, "bold"), text_color="#ffffff")
            lbl.pack(pady=(0, 5))
            self.labels[key] = lbl
            
        self.grid_columnconfigure((0, 1, 2), weight=1)

    def update_stats(self, stats):
        if not stats: return
        self.labels["min"].configure(text=f"{stats['min']:.3f}")
        self.labels["max"].configure(text=f"{stats['max']:.3f}")
        self.labels["range"].configure(text=f"{stats['range']:.3f}")
        self.labels["var"].configure(text=f"{stats['variance']:.4f}")
        self.labels["mean"].configure(text=f"{stats['mean']:.3f}")
        self.labels["rms"].configure(text=f"{stats['rms']:.3f}")