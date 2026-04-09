import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.patheffects as path_effects
import numpy as np

BG_COLOR = "#1a1a1a"

def clear_tab(tab):
    for w in tab.winfo_children():
        w.destroy()

def draw_2d_map(tab, matrix, bx, by, gx, gy):
    """
    Рисует карту gx x gy в виде четких квадратов.
    Цифры строго в центрах ячеек.
    """
    clear_tab(tab)
    plt.style.use('dark_background')
    
    fig = plt.figure(figsize=(6, 6), dpi=100)
    fig.patch.set_facecolor(BG_COLOR)
    ax = fig.add_subplot(111)
    ax.set_facecolor(BG_COLOR)
    
    # 'nearest' дает четкие границы плиток стола
    im = ax.imshow(matrix, cmap='RdYlBu_r', origin='lower', 
                   extent=[0, bx, 0, by], interpolation='nearest')
    
    # Расчет центров ячеек
    dx = bx / gx
    dy = by / gy
    centers_x = np.linspace(dx/2, bx - dx/2, gx)
    centers_y = np.linspace(dy/2, by - dy/2, gy)
    
    z_min, z_max = matrix.min(), matrix.max()
    threshold = (z_max + z_min) / 2
    
    for i in range(gy):
        for j in range(gx):
            val = matrix[i, j]
            t_color = "black" if (val > threshold and val > 0) else "white"
            
            t = ax.text(centers_x[j], centers_y[i], f"{val:+.3f}", 
                        ha="center", va="center", 
                        fontweight='bold', color=t_color, fontsize=9)
            
            t.set_path_effects([path_effects.withStroke(linewidth=2, foreground="#111111" if t_color=="white" else "#eeeeee")])
    
    ax.set_aspect('equal')
    ax.set_xlabel("X (мм)", fontsize=9, color="#888888")
    ax.set_ylabel("Y (мм)", fontsize=9, color="#888888")
    
    ax.set_xticks(np.linspace(0, bx, gx + 1))
    ax.set_yticks(np.linspace(0, by, gy + 1))
    
    ax.grid(color='#ffffff', linestyle='-', linewidth=0.8, alpha=0.1)
    
    for spine in ax.spines.values():
        spine.set_visible(False)

    canvas = FigureCanvasTkAgg(fig, master=tab)
    canvas.draw()
    canvas.get_tk_widget().pack(fill="both", expand=True)