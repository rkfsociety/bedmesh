import customtkinter as ctk
import stats_win, recs_win, strings_win, styles_win

class AnalysisPanel(ctk.CTkFrame):
    def __init__(self, parent, z_sys_default, pitch_default, refresh_cb):
        super().__init__(parent, width=360)
        self.pack_propagate(False)
        self.refresh_cb = refresh_cb
        
        # 1. Заголовок и статика
        ctk.CTkLabel(self, text="АНАЛИЗ МЕША", font=styles_win.FONTS["ui_bold"]).pack(pady=(15, 5))
        self.stats_block = stats_win.StatsBlock(self)
        self.stats_block.pack(fill="x", padx=15, pady=5)
        
        ctk.CTkLabel(self, text=strings_win.SECTION_ALIGN, font=styles_win.FONTS["ui_bold"]).pack(pady=(15, 5))
        
        # 2. Выбор системы
        self.z_m = ctk.CTkOptionMenu(self, values=strings_win.Z_SYSTEMS, command=self._on_sys_change)
        self.z_m.set(z_sys_default)
        self.z_m.pack(pady=10, padx=20, fill="x")
        
        # 3. Контейнер резьбы
        self.pitch_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.pitch_frame.pack(fill="x")
        
        self.p_l = ctk.CTkLabel(self.pitch_frame, text=strings_win.LBL_PITCH)
        self.p_l.pack()
        
        self.p_m = ctk.CTkOptionMenu(self.pitch_frame, values=["0.7", "0.5", "0.8"], command=refresh_cb)
        self.p_m.set(pitch_default)
        self.p_m.pack(pady=5, padx=20, fill="x")
        
        # 4. Скролл-зона рекомендаций
        self.rec_s = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.rec_s.pack(fill="both", expand=True, padx=5, pady=10)
        
        # КРИТИЧЕСКОЕ ИСПРАВЛЕНИЕ: 
        # Вызываем проверку видимости через 10мс, чтобы Tkinter успел упаковать rec_s
        self.after(10, lambda: self._check_pitch_visibility(z_sys_default))

    def _on_sys_change(self, choice):
        self._check_pitch_visibility(choice)
        self.refresh_cb()

    def _check_pitch_visibility(self, choice):
        # Проверяем, существует ли еще виджет (на случай быстрого закрытия)
        if not self.winfo_exists():
            return
            
        try:
            if "Валы" in choice:
                self.pitch_frame.pack_forget()
            else:
                # Теперь rec_s гарантированно упакован, ошибка не вылетит
                self.pitch_frame.pack(before=self.rec_s, fill="x")
        except Exception as e:
            # Если всё же случилась беда, просто пакуем в конец, чтобы не ронять прогу
            print(f"Layout warning: {e}")
            self.pitch_frame.pack(fill="x")

    def update_results(self, matrix, grid_x):
        stats = stats_win.get_mesh_stats(matrix)
        self.stats_block.update_stats(stats)
        
        recs, _ = recs_win.get_recs(matrix, self.z_m.get(), float(self.p_m.get()), int(grid_x))
        for w in self.rec_s.winfo_children(): w.destroy()
        for i in recs:
            recs_win.RecCard(self.rec_s, i['name'], i['val'], i['turns'], i['dir'])