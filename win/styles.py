import customtkinter as ctk

# Цвета Windows 11 Style
COLORS = {
    "dark": {"bg": "#1a1a1a", "card": "#242424", "accent": "#007acc", "success": "#28a745"},
    "light": {"bg": "#f9f9f9", "card": "#ffffff", "accent": "#007acc", "success": "#2ecc71"}
}

def get_fonts():
    return {
        "title": ctk.CTkFont(family="Segoe UI", size=16, weight="bold"),
        "body": ctk.CTkFont(family="Segoe UI", size=12),
        "code": ctk.CTkFont(family="Consolas", size=11)
    }