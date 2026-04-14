import customtkinter as ctk

# Цветовая палитра для единообразия на всех ПК
COLORS = {
    "bg_dark": "#1a1a1a",
    "bg_panel": "#2b2b2b",
    "accent": "#00ffcc",
    "text_main": "#ffffff",
    "text_dim": "#aaaaaa",
    "border": "#3d3d3d"
}

# Шрифты
FONTS = {
    "title": ("Segoe UI", 16, "bold"),
    "ui": ("Segoe UI", 12),
    "ui_bold": ("Segoe UI", 12, "bold"),
    "micro": ("Segoe UI", 10)
}

def apply_global_styles():
    """ 
    Принудительно устанавливаем темную тему. 
    Это убирает белые полосы у пользователей со светлой темой Windows.
    """
    ctk.set_appearance_mode("dark")  
    ctk.set_default_color_theme("blue")