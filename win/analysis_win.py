import customtkinter as ctk
import stats_win, recs_win, strings_win, styles_win

class AnalysisPanel(ctk.CTkFrame):
    def __init__(self, parent, z_sys_default, pitch_default, refresh_cb):
        super().__init__(parent, width=360)
        self.pack_propagate(False)
        
        ctk.CTkLabel(self, text="АНАЛИЗ МЕША", font=styles_win.FONTS["ui_bold"]).pack(pady=(15, 5))
        self.stats_block = stats_win.StatsBlock(self)
        self.stats_block.pack(fill="x", padx=15, pady=5)
        
        ctk.CTkLabel(self, text=strings_win.SECTION_ALIGN, font=styles_win.FONTS["ui_bold"]).pack(pady=(15, 5))
        self.z_m = ctk.CTkOptionMenu(self, values=strings_win.Z_SYSTEMS, command=refresh_cb)
        self.z_m.set(z_sys_default)
        self.z_m.pack(pady=10, padx=20, fill="x")
        
        self.p_l = ctk.CTkLabel(self, text=strings_win.LBL_PITCH); self.p_l.pack()
        self.p_m = ctk.CTkOptionMenu(self, values=["0.7", "0.5", "0.8"], command=refresh_cb)
        self.p_m.set(pitch_default)
        self.p_m.pack(pady=5, padx=20, fill="x")
        
        self.rec_s = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.rec_s.pack(fill="both", expand=True, padx=5, pady=10)

    def update_results(self, matrix, grid_x):
        stats = stats_win.get_mesh_stats(matrix)
        self.stats_block.update_stats(stats)
        recs, _ = recs_win.get_recs(matrix, self.z_m.get(), float(self.p_m.get()), int(grid_x))
        for w in self.rec_s.winfo_children(): w.destroy()
        for i in recs: recs_win.RecCard(self.rec_s, i['name'], i['val'], i['turns'], i['dir'])