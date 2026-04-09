import customtkinter as ctk
import styles_win, strings_win

class LabeledEntry(ctk.CTkFrame):
    def __init__(self, master, label_text, default_val="", show=None):
        super().__init__(master, fg_color="transparent")
        self.pack(fill="x", padx=20, pady=5)
        ctk.CTkLabel(self, text=label_text, font=styles_win.FONTS["micro"], text_color="#aaaaaa").pack(anchor="w")
        self.entry = ctk.CTkEntry(self, height=35, corner_radius=8, border_width=1)
        self.entry.insert(0, default_val)
        if show: self.entry.configure(show=show)
        self.entry.pack(fill="x", pady=(2, 0))
    def get(self): return self.entry.get()

class RecCard(ctk.CTkFrame):
    def __init__(self, master, name, val, turns, direction):
        color = styles_win.COLORS["dark"]["success"] if direction == strings_win.DIR_OK else \
                (styles_win.COLORS["dark"]["error"] if abs(val) > 0.1 else styles_win.COLORS["dark"]["warning"])
        super().__init__(master, fg_color=color, corner_radius=10)
        self.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(self, text=name, font=styles_win.FONTS["ui_bold"]).pack(pady=(5,0))
        txt = f"{val:+.3f} мм" + (f" ({turns})" if turns else "")
        ctk.CTkLabel(self, text=txt, font=styles_win.FONTS["ui"]).pack()
        ctk.CTkLabel(self, text=direction, font=styles_win.FONTS["micro"]).pack(pady=(0,5))