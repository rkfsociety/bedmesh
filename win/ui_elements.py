import customtkinter as ctk

class LabeledEntry(ctk.CTkFrame):
    def __init__(self, master, label, default="", show=None, **kwargs):
        super().__init__(master, fg_color="transparent")
        self.pack(pady=5, padx=20, fill="x")
        
        self.lbl = ctk.CTkLabel(self, text=label, font=("Segoe UI", 10), text_color="#858585")
        self.lbl.pack(anchor="w", padx=2)
        
        self.entry = ctk.CTkEntry(self, show=show, height=35)
        self.entry.insert(0, default)
        self.entry.pack(fill="x", pady=(2, 0))

    def get(self):
        return self.entry.get()

    def set(self, value):
        self.entry.delete(0, "end")
        self.entry.insert(0, str(value))