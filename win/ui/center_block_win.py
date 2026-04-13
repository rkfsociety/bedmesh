import customtkinter as ctk
from ui import map2d_win
from utils import strings_win

class CenterBlock(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent, fg_color="transparent")
        
        self.tabs = ctk.CTkTabview(self, fg_color="#2b2b2b")
        self.tabs.pack(fill="both", expand=True, padx=5, pady=5)
        
        self.tab_2d = self.tabs.add(strings_win.TAB_2D)
        self.map2d = map2d_win.MapCanvas(self.tab_2d)
        self.map2d.pack(fill="both", expand=True)
        
        self.tab_raw = self.tabs.add(strings_win.TAB_RAW)
        self.text_editor = ctk.CTkTextbox(self.tab_raw, font=("Consolas", 12))
        self.text_editor.pack(fill="both", expand=True)

    def update_display(self, matrix, gx, raw_data):
        if matrix is not None:
            self.map2d.draw(matrix, gx)
        if raw_data:
            self.text_editor.delete("1.0", "end")
            self.text_editor.insert("end", raw_data)