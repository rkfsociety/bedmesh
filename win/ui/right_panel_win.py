import customtkinter as ctk
import numpy as np
from core import calculator_win
from ui.recs_win import RecCard

class RightPanel(ctk.CTkFrame):
    def __init__(self, parent, z_sys, pitch, refresh_cb):
        super().__init__(parent, width=280, fg_color="#2b2b2b", corner_radius=15)
        self.refresh_cb = refresh_cb
        self.last_matrix = None
        self.last_gx = 5
        
        self.init_ui(z_sys, pitch)

    def init_ui(self, z_sys, pitch):
        ctk.CTkLabel(self, text="📝 АНАЛИЗ МЕША", font=("Segoe UI", 14, "bold")).pack(pady=(15, 10))
        
        self.f_stats = ctk.CTkFrame(self, fg_color="transparent")
        self.f_stats.pack(fill="x", padx=15)
        self.metrics = {}
        labels = [("Мин", "min"), ("Макс", "max"), ("Размах", "range"), 
                  ("Среднее", "mean"), ("Варианс", "var"), ("RMS", "rms")]
        
        for i, (name, key) in enumerate(labels):
            row, col = divmod(i, 2)
            f = ctk.CTkFrame(self.f_stats, fg_color="#333333", corner_radius=8)
            f.grid(row=row, column=col, padx=4, pady=4, sticky="nsew")
            ctk.CTkLabel(f, text=name, font=("Segoe UI", 10), text_color="#aaaaaa").pack()
            self.metrics[key] = ctk.CTkLabel(f, text="0.000", font=("Segoe UI", 12, "bold"), text_color="#00ffcc")
            self.metrics[key].pack()
            self.f_stats.grid_columnconfigure(col, weight=1)

        ctk.CTkLabel(self, text="—" * 15, text_color="#3d3d3d").pack(pady=10)
        
        self.z_m = ctk.CTkOptionMenu(self, values=["Винты (4шт)", "Винты (3шт)", "Валы (2 перед, 1 зад)", "Валы (4 по углам)"], 
                                     command=self._on_ui_change, fg_color="#3d3d3d")
        self.z_m.set(z_sys)
        self.z_m.pack(pady=5, padx=15, fill="x")
        
        self.p_m = ctk.CTkOptionMenu(self, values=["0.7", "0.5", "0.4", "0.8", "1.0", "2.0"], 
                                     command=self._on_ui_change, fg_color="#3d3d3d")
        self.p_m.set(str(pitch))
        self.p_m.pack(pady=5, padx=15, fill="x")

        self.res_area = ctk.CTkScrollableFrame(self, fg_color="transparent", height=250)
        self.res_area.pack(fill="both", expand=True, padx=10, pady=10)
        
        self._check_pitch_visibility(z_sys)

    def _on_ui_change(self, _=None):
        self._check_pitch_visibility(self.z_m.get())
        self.refresh_cb()
        if self.last_matrix is not None:
            self.update_results(self.last_matrix, self.last_gx)

    def _check_pitch_visibility(self, z_type):
        if "Валы" in z_type: self.p_m.pack_forget()
        else: self.p_m.pack(pady=5, padx=15, fill="x", after=self.z_m)

    def update_results(self, matrix, gx):
        if matrix is None: return
        self.last_matrix, self.last_gx = matrix, gx
        
        flat = matrix.flatten()
        self.metrics["min"].configure(text=f"{np.min(flat):.3f}")
        self.metrics["max"].configure(text=f"{np.max(flat):.3f}")
        self.metrics["range"].configure(text=f"{(np.max(flat)-np.min(flat)):.3f}")
        self.metrics["mean"].configure(text=f"{np.mean(flat):.3f}")
        self.metrics["var"].configure(text=f"{np.var(flat):.4f}")
        self.metrics["rms"].configure(text=f"{np.sqrt(np.mean(matrix**2)):.3f}")

        for w in self.res_area.winfo_children(): w.destroy()
        recs = calculator_win.get_recs(matrix, self.z_m.get(), float(self.p_m.get()), gx)
        for r in recs:
            RecCard(self.res_area, r['name'], r['val'], r['turns'], r['dir'])