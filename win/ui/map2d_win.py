import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import numpy as np
import matplotlib.colors as mcolors
import customtkinter as ctk

class MapCanvas(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent, fg_color="#2b2b2b")
        
        # Создаем фигуру Matplotlib с темным фоном
        self.fig, self.ax = plt.subplots(figsize=(8, 6), dpi=100)
        self.fig.patch.set_facecolor('#2b2b2b')
        self.ax.set_facecolor('#2b2b2b')
        
        # Интегрируем холст в CustomTkinter
        self.canvas = FigureCanvasTkAgg(self.fig, master=self)
        self.canvas_widget = self.canvas.get_tk_widget()
        self.canvas_widget.pack(fill="both", expand=True)

    def draw(self, matrix, gx):
        """Метод отрисовки карты (вызывается при получении новых данных)"""
        if matrix is None:
            return

        self.ax.clear()
        gy = matrix.shape[0]
        
        # Размеры стола (можно позже прокидывать из настроек через аргументы)
        bed_x = 250 
        bed_y = 250

        # Расчет цветовой схемы относительно среднего (Mean)
        avg_val = np.mean(matrix)
        v_min, v_max = matrix.min(), matrix.max()
        
        if v_min == v_max:
            v_min -= 0.1
            v_max += 0.1

        # Центрируем палитру (Красный - Низ, Зеленый - Верх)
        norm = mcolors.TwoSlopeNorm(vmin=v_min, vcenter=avg_val, vmax=v_max)
        
        # Отрисовка имиджа
        im = self.ax.imshow(matrix, cmap='RdYlGn', interpolation='nearest', origin='lower',
                            extent=[0, bed_x, 0, bed_y], norm=norm, alpha=0.9)
        
        # Добавляем текстовые значения в каждую ячейку
        step_x = bed_x / gx
        step_y = bed_y / gy

        for y in range(gy):
            for x in range(gx):
                val = matrix[y, x]
                pos_x = (x * step_x) + (step_x / 2)
                pos_y = (y * step_y) + (step_y / 2)
                
                self.ax.text(pos_x, pos_y, f"{val:+.3f}", 
                            ha="center", va="center", 
                            color="black", fontsize=9, fontweight='bold')

        # Оформление осей
        self.ax.set_xlabel("X (мм)", color='white')
        self.ax.set_ylabel("Y (мм)", color='white')
        self.ax.tick_params(colors='white')
        
        self.canvas.draw()