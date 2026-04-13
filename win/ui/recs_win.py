import customtkinter as ctk

class RecCard(ctk.CTkFrame):
    def __init__(self, parent, name, val, turns, direction):
        super().__init__(parent, fg_color="#333333", corner_radius=8)
        self.pack(fill="x", pady=2, padx=5)
        
        if turns is None:
            # Текст для валов
            text = f"{name}: {val:+.3f} мм"
        else:
            # Текст для винтов
            display_turns = turns if turns > 0.001 else 0.0
            text = f"{name}: {val:+.3f} мм\n({display_turns:.2f} об. {direction})"
            
        self.label = ctk.CTkLabel(
            self, 
            text=text, 
            font=("Segoe UI", 12, "bold"), 
            justify="left"
        )
        self.label.pack(pady=8, padx=10)