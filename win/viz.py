import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.patheffects as path_effects
import numpy as np
from mpl_toolkits.mplot3d import Axes3D
from scipy.interpolate import griddata # Для сглаживания поверхности

BG_COLOR = "#1a1a1a"

def clear_tab(tab):
    for w in tab.winfo_children(): w.destroy()

def draw_2d_map(tab, matrix, bx, by, gx, gy):
    clear_tab(tab)
    plt.style.use('dark_background')
    fig = plt.figure(figsize=(6, 6), dpi=100); fig.patch.set_facecolor(BG_COLOR)
    ax = fig.add_subplot(111); ax.set_facecolor(BG_COLOR)
    xe, ye = np.linspace(0, bx, gx + 1), np.linspace(0, by, gy + 1)
    im = ax.pcolormesh(xe, ye, matrix, cmap='RdYlBu_r', edgecolors='black', linewidth=0.5)
    xc, yc = (xe[:-1] + xe[1:]) / 2, (ye[:-1] + ye[1:]) / 2
    for i in range(gy):
        for j in range(gx):
            t = ax.text(xc[j], yc[i], f"{matrix[i,j]:.3f}", ha="center", va="center", fontweight='bold', color="white", fontsize=8)
            t.set_path_effects([path_effects.withStroke(linewidth=2, foreground="black")])
    ax.set_aspect('equal')
    ax.set_xlabel("X (мм)", fontsize=9); ax.set_ylabel("Y (мм)", fontsize=9)
    FigureCanvasTkAgg(fig, master=tab).get_tk_widget().pack(fill="both", expand=True)

def draw_3d_klipper_style(tab, matrix, bx, by, gx, gy):
    clear_tab(tab)
    plt.style.use('dark_background')
    fig = plt.figure(figsize=(7, 7), dpi=100); fig.patch.set_facecolor(BG_COLOR)
    ax = fig.add_subplot(111, projection='3d'); ax.set_facecolor(BG_COLOR)
    
    # 1. Сглаживание данных (Интерполяция как в Plotly)
    x = np.linspace(0, bx, gx)
    y = np.linspace(0, by, gy)
    X, Y = np.meshgrid(x, y)
    
    # Создаем более плотную сетку для плавности
    x_fine = np.linspace(0, bx, 50)
    y_fine = np.linspace(0, by, 50)
    X_fine, Y_fine = np.meshgrid(x_fine, y_fine)
    Z_fine = griddata((X.flatten(), Y.flatten()), matrix.flatten(), (X_fine, Y_fine), method='cubic')

    # 2. Отрисовка поверхности
    # Используем цветовую схему 'jet' или 'RdYlBu_r'
    surf = ax.plot_surface(X_fine, Y_fine, Z_fine, cmap='jet', edgecolor='none', 
                          antialiased=True, alpha=0.9, shade=True)
    
    # 3. Накладываем редкую черную сетку поверх для стиля
    ax.plot_wireframe(X, Y, matrix, color='black', linewidth=0.4, alpha=0.5)

    # 4. Чистим интерфейс (убираем серые стенки)
    ax.xaxis.set_pane_color((0,0,0,0)); ax.yaxis.set_pane_color((0,0,0,0)); ax.zaxis.set_pane_color((0,0,0,0))
    grid_style = {'color': '#444444', 'linewidth': 0.5}
    ax.xaxis._axinfo["grid"].update(grid_style); ax.yaxis._axinfo["grid"].update(grid_style); ax.zaxis._axinfo["grid"].update(grid_style)

    ax.set_xlabel('X', fontsize=8); ax.set_ylabel('Y', fontsize=8); ax.set_zlabel('Z', fontsize=8)
    ax.view_init(elev=25, azim=-135)
    ax.mouse_init() # Включаем вращение

    FigureCanvasTkAgg(fig, master=tab).get_tk_widget().pack(fill="both", expand=True)