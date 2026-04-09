import customtkinter as ctk
import styles

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

class RecCard(ctk.CTkFrame):
    """ Карточка рекомендации для одной точки стола """
    def __init__(self, master, name, value, turns_info, direction, **kwargs):
        # Выбор цвета в зависимости от отклонения
        abs_val = abs(value)
        if abs_val == 0: color = styles.COLORS["dark"]["success"]
        elif abs_val <= 0.2: color = styles.COLORS["dark"]["warning"]
        else: color = styles.COLORS["dark"]["danger"]

        super().__init__(master, fg_color=styles.COLORS["dark"]["card"], border_width=2, border_color=color)
        self.pack(pady=5, padx=10, fill="x")

        # Название точки
        self.title = ctk.CTkLabel(self, text=name, font=styles.FONTS["ui_bold"], text_color=styles.COLORS["dark"]["text"])
        self.title.pack(anchor="w", padx=10, pady=(5, 0))

        # Значение и направление
        self.info_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.info_frame.pack(fill="x", padx=10, pady=(0, 5))

        val_text = f"{value:+.3f} мм"
        if turns_info: val_text += f"\n({turns_info.strip(' |')})"
        
        self.val_lbl = ctk.CTkLabel(self.info_frame, text=val_text, font=styles.FONTS["ui"], justify="left")
        self.val_lbl.pack(side="left")

        self.dir_lbl = ctk.CTkLabel(self.info_frame, text=direction, font=styles.FONTS["ui_bold"], text_color=color)
        self.dir_lbl.pack(side="right")