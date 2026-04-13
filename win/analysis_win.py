import customtkinter as ctk
import numpy as np

class AnalysisPanel(ctk.CTkFrame):
    def __init__(self, parent, z_sys, pitch, refresh_cb):
        super().__init__(parent, width=280, fg_color="#2b2b2b", corner_radius=15)
        self.refresh_cb = refresh_cb
        self.init_ui(z_sys, pitch)

    def init_ui(self, z_sys, pitch):
        # Заголовок панели
        ctk.CTkLabel(self, text="📝 АНАЛИЗ МЕША", font=("Segoe UI", 14, "bold")).pack(pady=(15, 10))
        
        # Сетка статистических метрик (Плитки)
        self.f_stats = ctk.CTkFrame(self, fg_color="transparent")
        self.f_stats.pack(fill="x", padx=15)
        
        self.metrics = {}
        labels = [
            ("Мин. точка", "min"), ("Макс. точка", "max"),
            ("Размах (Range)", "range"), ("Среднее (Mean)", "mean"),
            ("Вариация", "var"), ("Среднеквадр. (RMS)", "rms")
        ]
        
        for i, (name, key) in enumerate(labels):
            row, col = divmod(i, 2)
            f = ctk.CTkFrame(self.f_stats, fg_color="#333333", corner_radius=8)
            f.grid(row=row, column=col, padx=4, pady=4, sticky="nsew")
            
            ctk.CTkLabel(f, text=name, font=("Segoe UI", 10), text_color="#aaaaaa").pack(pady=(5, 0))
            self.metrics[key] = ctk.CTkLabel(f, text="0.000", font=("Segoe UI", 12, "bold"), text_color="#00ffcc")
            self.metrics[key].pack(pady=(0, 5))
            self.f_stats.grid_columnconfigure(col, weight=1)

        ctk.CTkLabel(self, text="—" * 15, text_color="#3d3d3d").pack(pady=10)
        
        # Выбор механики (Селекторы)
        self.z_m = ctk.CTkOptionMenu(self, values=["Винты (углы)", "2 вала (Л/П)", "3 вала (Tri-Z)", "4 вала (Quad-Z)"], 
                                     command=self.refresh_cb, fg_color="#3d3d3d", button_color="#4d4d4d")
        self.z_m.set(z_sys)
        self.z_m.pack(pady=5, padx=15, fill="x")
        
        self.p_m = ctk.CTkOptionMenu(self, values=["0.7", "0.5", "0.4", "0.8", "1.0", "2.0"], 
                                     command=self.refresh_cb, fg_color="#3d3d3d", button_color="#4d4d4d")
        self.p_m.set(pitch)
        self.p_m.pack(pady=5, padx=15, fill="x")

        # Область вывода рекомендаций
        self.res_area = ctk.CTkScrollableFrame(self, fg_color="transparent", height=250)
        self.res_area.pack(fill="both", expand=True, padx=10, pady=10)

    def update_results(self, matrix, gx):
        # 1. Обновление цифровой статистики
        flat = matrix.flatten()
        self.metrics["min"].configure(text=f"{np.min(flat):.3f}")
        self.metrics["max"].configure(text=f"{np.max(flat):.3f}")
        self.metrics["range"].configure(text=f"{(np.max(flat) - np.min(flat)):.3f}")
        self.metrics["mean"].configure(text=f"{np.mean(flat):.3f}")
        self.metrics["var"].configure(text=f"{np.var(flat):.4f}")
        self.metrics["rms"].configure(text=f"{np.sqrt(np.mean(matrix**2)):.3f}")

        # 2. Очистка старых рекомендаций
        for w in self.res_area.winfo_children(): w.destroy()
        
        # 3. Настройка видимости селектора шага (скрываем для валов)
        z_type = self.z_m.get()
        is_shafts = "вала" in z_type.lower()
        if is_shafts:
            self.p_m.pack_forget()
        else:
            self.p_m.pack(pady=5, padx=15, fill="x", after=self.z_m)
        
        pitch = float(self.p_m.get())
        points = {}
        gx = int(gx)
        
        # 4. Сбор точек в зависимости от механики
        if "Винты" in z_type or "4 вала" in z_type:
            points = {"ПЛ (0,0)": matrix[0,0], "ПП (X,0)": matrix[0,-1], "ЗЛ (0,Y)": matrix[-1,0], "ЗП (X,Y)": matrix[-1,-1]}
        elif "2 вала" in z_type:
            points = {"Левый вал": np.mean(matrix[:, 0]), "Правый вал": np.mean(matrix[:, -1])}
        elif "3 вала" in z_type:
            points = {"ПЛ": matrix[0,0], "ПП": matrix[0,-1], "З-Центр": matrix[-1, gx//2]}

        # 5. Отрисовка карточек рекомендаций
        low = min(points.values())
        for name, val in points.items():
            diff = val - low
            # Цвет фона: зеленый для опоры, темно-серый для остальных
            bg_col = "#2e7d32" if diff < 0.005 else "#333333"
            frame = ctk.CTkFrame(self.res_area, fg_color=bg_col, corner_radius=8)
            frame.pack(fill="x", pady=2)
            
            ctk.CTkLabel(frame, text=name, font=("Segoe UI", 11, "bold")).pack(side="left", padx=10, pady=5)
            
            if diff < 0.005:
                res_txt = "ОПОРА"
                color = "#00ffcc"
            else:
                direction = "🔽" if diff > 0 else "🔼"
                if is_shafts:
                    res_txt = f"{abs(diff):.3f} мм {direction}"
                else:
                    res_txt = f"{abs(diff/pitch):.2f} об. {direction}"
                color = "#ffcc00"
                
            ctk.CTkLabel(frame, text=res_txt, font=("Segoe UI", 11), text_color=color).pack(side="right", padx=10)