import customtkinter as ctk
import numpy as np
import styles_win
import strings_win

def get_recs(matrix, z_type, pitch, gx):
    """Расчет необходимых правок для выравнивания стола"""
    is_screws = "Винты" in z_type
    if is_screws or "4 вала" in z_type:
        pts = {"ПЛ (0,0)": matrix[0,0], "ПП (X,0)": matrix[0,-1], "ЗЛ (0,Y)": matrix[-1,0], "ЗП (X,Y)": matrix[-1,-1]}
    elif "2 вала" in z_type:
        pts = {"Левый вал": np.mean(matrix[:, 0]), "Правый вал": np.mean(matrix[:, -1])}
    elif "3 вала" in z_type:
        pts = {"Перед Лево": matrix[0,0], "Перед Право": matrix[0,-1], "Зад Центр": matrix[-1, gx//2]}
    else: 
        pts = {"ПЛ": matrix[0,0], "ПП": matrix[0,-1], "ЗЛ": matrix[-1,0], "ЗП": matrix[-1,-1]}
    
    vals = list(pts.values())
    avg_val = sum(vals) / len(vals)
    best_ref_key = min(pts, key=lambda k: abs(pts[k] - avg_val))
    ref_val = pts[best_ref_key]
    res_data = []
    for name, val in pts.items():
        diff = val - ref_val
        direction = strings_win.DIR_OK if name == best_ref_key else (strings_win.DIR_DOWN if diff > 0 else strings_win.DIR_UP)
        t_info = f"{abs(diff/pitch):.2f} об." if is_screws else ""
        res_data.append({"name": name, "val": diff, "turns": t_info, "dir": direction})
    return res_data, is_screws

class RecCard(ctk.CTkFrame):
    """Карточка рекомендации для правой панели"""
    def __init__(self, master, name, val, turns, direction):
        color = styles_win.COLORS["dark"]["success"] if direction == strings_win.DIR_OK else \
                (styles_win.COLORS["dark"]["error"] if abs(val) > 0.1 else styles_win.COLORS["dark"]["warning"])
        super().__init__(master, fg_color=color, corner_radius=10)
        self.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(self, text=name, font=styles_win.FONTS["ui_bold"]).pack(pady=(5,0))
        txt = f"{val:+.3f} мм" + (f" ({turns})" if turns else "")
        ctk.CTkLabel(self, text=txt, font=styles_win.FONTS["ui"]).pack()
        ctk.CTkLabel(self, text=direction, font=styles_win.FONTS["micro"]).pack(pady=(0,5))