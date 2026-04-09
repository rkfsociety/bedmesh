import customtkinter as ctk
import sys

# На macOS используем Helvetica/Menlo, на остальных - Segoe UI/Consolas
FONT_NAME = "Helvetica" if sys.platform == "darwin" else "Segoe UI"
CODE_FONT = "Menlo" if sys.platform == "darwin" else "Consolas"

COLORS = {
    "dark": {
        "bg": "#1a1a1a", 
        "card": "#242424", 
        "accent": "#007acc", 
        "success": "#28a745", 
        "warning": "#d19a66", 
        "danger": "#f44336", 
        "text": "#d4d4d4",
        "text_dim": "#858585"
    }
}

FONTS = {
    "title": (FONT_NAME, 16, "bold"),
    "ui": (FONT_NAME, 12),
    "ui_bold": (FONT_NAME, 12, "bold"),
    "code": (CODE_FONT, 11),
    "micro": (FONT_NAME, 10)
}