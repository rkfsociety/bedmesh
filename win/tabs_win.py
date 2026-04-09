import customtkinter as ctk
import ui_elements_win, styles_win, config_win

class SettingsTab(ctk.CTkScrollableFrame):
    def __init__(self, parent, create_bak_cb, restore_bak_cb, save_cb):
        super().__init__(parent, fg_color="transparent")
        
        self.bf = ctk.CTkFrame(self, fg_color="#2b2b2b", corner_radius=10)
        self.bf.pack(fill="x", pady=10, padx=10)
        bg = ctk.CTkFrame(self.bf, fg_color="transparent")
        bg.pack(fill="x", pady=5, padx=10)
        
        ctk.CTkButton(bg, text="СОЗДАТЬ БЭКАП (.bak)", fg_color="#444444", command=create_bak_cb).pack(side="left", expand=True, padx=5, pady=5)
        ctk.CTkButton(bg, text="ВОССТАНОВИТЬ БЭКАП", fg_color="#554444", command=restore_bak_cb).pack(side="left", expand=True, padx=5, pady=5)
        
        ctk.CTkLabel(self, text="Настройка тензодатчика [cs1237]", font=styles_win.FONTS["ui_bold"]).pack(pady=(20, 5))
        self.s1 = ui_elements_win.LabeledEntry(self, "sensitivity", "")
        self.s2 = ui_elements_win.LabeledEntry(self, "head_block_sensitivity", "")
        self.s3 = ui_elements_win.LabeledEntry(self, "scratch_sensitivity", "")
        
        ctk.CTkLabel(self, text="Параметры калибровки [leviQ3]", font=styles_win.FONTS["ui_bold"]).pack(pady=(20, 5))
        self.bed_t = ui_elements_win.LabeledEntry(self, "bed_temp", "")
        
        ctk.CTkButton(self, text="💾 СОХРАНИТЬ В ПРИНТЕР", height=50, fg_color="#d32f2f", command=save_cb).pack(pady=20, padx=20, fill="x")

    def update_values(self, content):
        self.s1.entry.delete(0, 'end'); self.s1.entry.insert(0, config_win.get_cfg_value(content, "cs1237", "sensitivity"))
        self.s2.entry.delete(0, 'end'); self.s2.entry.insert(0, config_win.get_cfg_value(content, "cs1237", "head_block_sensitivity"))
        self.s3.entry.delete(0, 'end'); self.s3.entry.insert(0, config_win.get_cfg_value(content, "cs1237", "scratch_sensitivity"))
        self.bed_t.entry.delete(0, 'end'); self.bed_t.entry.insert(0, config_win.get_cfg_value(content, "leviQ3", "bed_temp"))

    def get_form_data(self):
        return {"s1": self.s1.get(), "s2": self.s2.get(), "s3": self.s3.get(), "bed_t": self.bed_t.get()}