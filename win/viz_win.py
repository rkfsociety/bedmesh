import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.patheffects as path_effects
import numpy as np

BG_COLOR = "#1a1a1a"

def clear_tab(tab):
    for w in tab.winfo_children():
        w.destroy()

def draw_2d_map(tab, matrix, bx, by, gx, gy):
    """2D карта с мягкой интерполяцией и сеткой"""
    clear_tab(tab)
    plt.style.use('dark_background')
    fig = plt.figure(figsize=(6, 6), dpi=100)
    fig.patch.set_facecolor(BG_COLOR)
    ax = fig.add_subplot(111)
    ax.set_facecolor(BG_COLOR)
    
    # Интерполяция 'quadric' дает плавные переходы цветов
    # origin='lower' чтобы (0,0) был в левом нижнем углу
    im = ax.imshow(matrix, cmap='RdYlBu_r', origin='lower', 
                   extent=[0, bx, 0, by], interpolation='quadric')
    
    # Координаты точек для подписей
    xe = np.linspace(0, bx, gx)
    ye = np.linspace(0, by, gy)
    
    # Добавление числовых значений
    for i in range(gy):
        for j in range(gx):
            val = matrix[i, j]
            t = ax.text(xe[j], ye[i], f"{val:.3f}", ha="center", va="center", 
                        fontweight='bold', color="white", fontsize=8)
            # Обводка текста, чтобы его было видно на любом фоне
            t.set_path_effects([path_effects.withStroke(linewidth=2, foreground="black")])
    
    ax.set_aspect('equal')
    ax.set_xlabel("X (мм)", fontsize=9)
    ax.set_ylabel("Y (мм)", fontsize=9)
    
    # Легкая сетка поверх градиента
    ax.set_xticks(xe)
    ax.set_yticks(ye)
    ax.grid(color='#ffffff', linestyle='--', linewidth=0.5, alpha=0.2)

    canvas = FigureCanvasTkAgg(fig, master=tab)
    canvas.draw()
    canvas.get_tk_widget().pack(fill="both", expand=True)