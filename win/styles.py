import customtkinter as ctk

# Современная палитра Windows 11
COLORS = {
    "dark": {
        "bg": "#1a1a1a", 
        "card": "#242424", 
        "accent": "#007acc", 
        "success": "#28a745", # Зеленый (до 0.1мм)
        "warning": "#d19a66", # Оранжевый (до 0.3мм)
        "danger": "#f44336",  # Красный (более 0.3мм)
        "text": "#d4d4d4",
        "text_dim": "#858585"
    },
    "light": {
        "bg": "#f9f9f9", 
        "card": "#ffffff", 
        "accent": "#007acc", 
        "success": "#2ecc71",
        "warning": "#f39c12",
        "danger": "#e74c3c",
        "text": "#333333",
        "text_dim": "#666666"
    }
}

FONTS = {
    "title": ("Segoe UI", 16, "bold"),
    "ui": ("Segoe UI", 12),
    "ui_bold": ("Segoe UI", 12, "bold"),
    "code": ("Consolas", 11),
    "micro": ("Segoe UI", 10)
}