import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.patheffects as path_effects
import numpy as np
from mpl_toolkits.mplot3d import Axes3D
import styles

BG_COLOR_HEX = "#1a1a1a"

def clear_tab(tab):
    for w in tab.winfo_children():
        w.destroy()

def draw_2d_map(tab, matrix, bx, by, gx, gy):
    clear_tab(tab)
    plt.style.use('dark_background')
    fig = plt.figure(figsize=(6, 6), dpi=100)
    fig.patch.set_facecolor(BG_COLOR_HEX)
    
    ax = fig.add_subplot(111)
    ax.set_facecolor(BG_COLOR_HEX)
    
    xe = np.linspace(0, bx, gx + 1)
    ye = np.linspace(0, by, gy + 1)
    
    im = ax.pcolormesh(xe, ye, matrix, cmap='RdYlBu_r', edgecolors='black', linewidth=0.5)
    
    xc, yc = (xe[:-1] + xe[1:]) / 2, (ye[:-1] + ye[1:]) / 2
    for i in range(gy):
        for j in range(gx):
            val = matrix[i,j]
            # Исправлено: передаем параметры шрифта отдельно, а не кортежем
            t = ax.text(xc[j], yc[i], f"{val:.3f}", ha="center", va="center", 
                        fontweight='bold', color="white", fontsize=8)
            t.set_path_effects([path_effects.withStroke(linewidth=2, foreground="black")])
    
    ax.set_aspect('equal')
    # Исправлено: указываем только размер, чтобы избежать конфликта с FontProperties
    ax.set_xlabel("X (мм)", fontsize=9)
    ax.set_ylabel("Y (мм)", fontsize=9)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    
    canvas = FigureCanvasTkAgg(fig, master=tab)
    canvas.draw()
    canvas.get_tk_widget().pack(fill="both", expand=True)

def draw_3d_klipper_style(tab, matrix, bx, by, gx, gy):
    clear_tab(tab)
    plt.style.use('dark_background')
    fig = plt.figure(figsize=(7, 7), dpi=100)
    fig.patch.set_facecolor(BG_COLOR_HEX)
    
    ax = fig.add_subplot(111, projection='3d')
    ax.set_facecolor(BG_COLOR_HEX)
    
    X, Y = np.meshgrid(np.linspace(0, bx, gx), np.linspace(0, by, gy))
    
    surf = ax.plot_surface(X, Y, matrix, cmap='jet', edgecolor='black', 
                          linewidth=0.3, antialiased=True, alpha=0.9)
    
    ax.xaxis.set_pane_color((0,0,0,0))
    ax.yaxis.set_pane_color((0,0,0,0))
    ax.zaxis.set_pane_color((0,0,0,0))
    
    grid_col = "#444444"
    ax.xaxis._axinfo["grid"]['color'] = grid_col
    ax.yaxis._axinfo["grid"]['color'] = grid_col
    ax.zaxis._axinfo["grid"]['color'] = grid_col

    # Исправлено: параметры шрифта передаются без использования кортежей из styles.py
    ax.set_xlabel('X', fontsize=9, labelpad=5)
    ax.set_ylabel('Y', fontsize=9, labelpad=5)
    ax.set_zlabel('Z', fontsize=9, labelpad=5)
    
    ax.view_init(elev=30, azim=-120)

    # Интерактивность
    ax.mouse_init()

    canvas = FigureCanvasTkAgg(fig, master=tab)
    canvas.draw()
    canvas.get_tk_widget().pack(fill="both", expand=True)