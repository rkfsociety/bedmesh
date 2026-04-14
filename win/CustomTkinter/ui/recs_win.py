import customtkinter as ctk
from utils import strings_win

class RecCard(ctk.CTkFrame):
    def __init__(self, master, name, val, turns, direction):
        # Подбираем цвет в зависимости от направления из strings_win
        is_down = (direction == strings_win.DIR_DOWN)
        color_theme = "#ff4d4d" if is_down else "#4dff88"
        
        super().__init__(master, fg_color="#333333", corner_radius=10, border_width=1, border_color="#444444")
        self.pack(fill="x", pady=6, padx=2)
        
        # Название точки
        self.lbl_name = ctk.CTkLabel(
            self, 
            text=name.upper(), 
            font=("Segoe UI", 11, "bold"), 
            text_color="#bbbbbb"
        )
        self.lbl_name.pack(anchor="w", padx=12, pady=(8, 2))
        
        self.info_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.info_frame.pack(fill="x", padx=12, pady=(0, 8))
        
        # Значение
        sign = "+" if is_down else "-"
        self.lbl_val = ctk.CTkLabel(
            self.info_frame, 
            text=f"{sign}{val:.3f} мм", 
            font=("Segoe UI", 14, "bold"), 
            text_color="#ffffff"
        )
        self.lbl_val.pack(side="left")
        
        # Рекомендация
        rec_text = f"({turns:.2f} об. {direction})"
        self.lbl_rec = ctk.CTkLabel(
            self.info_frame, 
            text=rec_text, 
            font=("Segoe UI", 12, "bold"), 
            text_color=color_theme
        )
        self.lbl_rec.pack(side="right")