import customtkinter as ctk

class LabeledEntry(ctk.CTkFrame):
    def __init__(self, master, label, default="", show=None, **kwargs):
        super().__init__(master, fg_color="transparent")
        self.pack(pady=5, padx=20, fill="x")
        ctk.CTkLabel(self, text=label, font=("Segoe UI", 10)).pack(anchor="w")
        self.entry = ctk.CTkEntry(self, show=show)
        self.entry.insert(0, default)
        self.entry.pack(fill="x", pady=(2, 0))

    def get(self): return self.entry.get()