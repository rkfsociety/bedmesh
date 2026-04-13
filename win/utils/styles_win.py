import customtkinter as ctk

# Цветовая палитра
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
    """Принудительная установка темной темы для всех систем"""
    ctk.set_appearance_mode("dark")  # Игнорируем светлую тему Windows
    ctk.set_default_color_theme("blue") # Базовая тема (можно "green" или "dark-blue")