import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.patheffects as path_effects
from matplotlib.colors import LightSource
import numpy as np
from scipy.interpolate import griddata

BG_COLOR = "#1a1a1a"

def clear_tab(tab):
    for w in tab.winfo_children(): w.destroy()

def draw_2d_map(tab, matrix, bx, by, gx, gy):
    clear_tab(tab)
    plt.style.use('dark_background')
    fig = plt.figure(figsize=(6, 6), dpi=100); fig.patch.set_facecolor(BG_COLOR)
    ax = fig.add_subplot(111); ax.set_facecolor(BG_COLOR)
    
    xe, ye = np.linspace(0, bx, gx + 1), np.linspace(0, by, gy + 1)
    ax.pcolormesh(xe, ye, matrix, cmap='RdYlBu_r', edgecolors='#222222', linewidth=0.5)
    
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
    
    # 1. Сглаживание (Cubic Interpolation)
    x, y = np.linspace(0, bx, gx), np.linspace(0, by, gy)
    X, Y = np.meshgrid(x, y)
    x_fine, y_fine = np.linspace(0, bx, 80), np.linspace(0, by, 80)
    X_f, Y_f = np.meshgrid(x_fine, y_fine)
    Z_f = griddata((X.ravel(), Y.ravel()), matrix.ravel(), (X_f, Y_f), method='cubic')

    # 2. Имитация освещения (как на GPU)
    ls = LightSource(azdeg=315, altdeg=45)
    # Создаем карту цветов с учетом теней
    rgb = ls.shade(Z_f, cmap=plt.get_cmap('jet'), vert_exag=0.1, blend_mode='soft')

    # 3. Отрисовка плавной поверхности
    ax.plot_surface(X_f, Y_f, Z_f, facecolors=rgb, rstride=1, cstride=1, 
                    antialiased=True, linewidth=0, shade=False)
    
    # Тонкая проволочная сетка для структуры
    ax.plot_wireframe(X, Y, matrix, color='white', linewidth=0.2, alpha=0.3)

    # Чистка осей
    ax.xaxis.set_pane_color((0,0,0,0)); ax.yaxis.set_pane_color((0,0,0,0)); ax.zaxis.set_pane_color((0,0,0,0))
    ax.xaxis._axinfo["grid"].update({'color': '#444444', 'linewidth': 0.5})
    ax.yaxis._axinfo["grid"].update({'color': '#444444', 'linewidth': 0.5})
    ax.zaxis._axinfo["grid"].update({'color': '#444444', 'linewidth': 0.5})

    ax.view_init(elev=30, azim=-135)
    ax.mouse_init()

    FigureCanvasTkAgg(fig, master=tab).get_tk_widget().pack(fill="both", expand=True)