import customtkinter as ctk
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.patheffects as path_effects
import numpy as np

class MapCanvas(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent, fg_color="transparent")
        
        # Создаем фигуру. Убираем фиксированный размер, чтобы она была гибкой
        self.fig, self.ax = plt.subplots(dpi=100)
        self.fig.patch.set_facecolor('#2b2b2b') 
        
        self.canvas = FigureCanvasTkAgg(self.fig, master=self)
        self.canvas_widget = self.canvas.get_tk_widget()
        self.canvas_widget.pack(fill="both", expand=True)
        
        self.ax.set_facecolor('#1a1a1a')
        self.ax.tick_params(colors='white', labelsize=10)

        # Обработка события изменения размера окна
        self.bind("<Configure>", self._on_resize)
        
        self.show_default_map()

    def _on_resize(self, event):
        """Принудительная перерисовка при изменении размера"""
        self.fig.tight_layout()
        self.canvas.draw_idle()

    def show_default_map(self):
        default_matrix = np.zeros((5, 5))
        self.draw(default_matrix, 5)

    def draw(self, matrix, gx):
        self.ax.clear()
        if matrix is None: return

        try:
            app_settings = self.master.master.settings
            bed_x = float(app_settings.get("bed_x", 250))
            bed_y = float(app_settings.get("bed_y", 250))
        except:
            bed_x, bed_y = 250.0, 250.0

        rows, cols = matrix.shape

        im = self.ax.imshow(
            matrix, 
            cmap='Spectral_r', 
            interpolation='nearest', 
            origin='lower',
            extent=[0, bed_x, 0, bed_y]
        )
        
        self.ax.set_title("Карта высот стола (мм)", color='white', pad=20, 
                          fontname="Segoe UI", fontsize=14, fontweight='bold')

        self.ax.set_xlabel("Ось X (мм)", color='#bbbbbb', fontsize=11, labelpad=10)
        self.ax.set_ylabel("Ось Y (мм)", color='#bbbbbb', fontsize=11, labelpad=10)

        x_centers = np.linspace(bed_x/(cols*2), bed_x - bed_x/(cols*2), cols)
        y_centers = np.linspace(bed_y/(rows*2), bed_y - bed_y/(rows*2), rows)

        for i in range(rows):
            for j in range(cols):
                val = matrix[i, j]
                txt = self.ax.text(
                    x_centers[j], y_centers[i], f"{val:+.3f}", 
                    ha="center", va="center", 
                    color='white', fontsize=12, fontweight='black' 
                )
                txt.set_path_effects([path_effects.withStroke(linewidth=4, foreground='black')])

        self.ax.set_xticks(np.linspace(0, bed_x, cols + 1), minor=True)
        self.ax.set_yticks(np.linspace(0, bed_y, rows + 1), minor=True)
        self.ax.grid(which="minor", color="#1a1a1a", linestyle='-', linewidth=2.5)
        
        self.ax.set_xticks(np.linspace(0, bed_x, 5))
        self.ax.set_yticks(np.linspace(0, bed_y, 5))
        
        for spine in self.ax.spines.values():
            spine.set_visible(False)

        self.fig.tight_layout()
        self.canvas.draw()