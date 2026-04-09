import customtkinter as ctk
import styles_win

class LabeledEntry(ctk.CTkFrame):
    """Поле ввода с заголовком сверху"""
    def __init__(self, master, label_text, default_val="", show=None):
        super().__init__(master, fg_color="transparent")
        self.pack(fill="x", padx=20, pady=5)
        ctk.CTkLabel(self, text=label_text, font=styles_win.FONTS["micro"], text_color="#aaaaaa").pack(anchor="w")
        self.entry = ctk.CTkEntry(self, height=35, corner_radius=8, border_width=1)
        self.entry.insert(0, default_val)
        if show: self.entry.configure(show=show)
        self.entry.pack(fill="x", pady=(2, 0))
    def get(self): return self.entry.get()