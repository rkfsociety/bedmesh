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
        
        self.raw_tab_exists = False
        self.text_editor = None

    def show_raw_tab(self):
        """Создает вкладку RAW, если её нет"""
        if not self.raw_tab_exists:
            tab_name = strings_win.TAB_RAW
            self.tabs.add(tab_name)
            self.text_editor = ctk.CTkTextbox(self.tabs.tab(tab_name), font=("Consolas", 12))
            self.text_editor.pack(fill="both", expand=True, padx=10, pady=10)
            self.raw_tab_exists = True

    def hide_raw_tab(self):
        """Удаляет вкладку RAW"""
        if self.raw_tab_exists:
            self.tabs.delete(strings_win.TAB_RAW)
            self.raw_tab_exists = False
            self.text_editor = None

    def update_display(self, matrix, gx, raw_data):
        """Обновляет карту и текст (если вкладка текста открыта)"""
        if matrix is not None:
            self.map2d.draw(matrix, gx)
            
        if raw_data and self.text_editor:
            self.text_editor.delete("1.0", "end")
            self.text_editor.insert("end", raw_data)