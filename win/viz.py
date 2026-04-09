import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.patheffects as path_effects
from matplotlib.colors import LightSource
import numpy as np
from scipy.interpolate import griddata
import styles

BG_COLOR = "#1a1a1a"

def clear_tab(tab):
    for w in tab.winfo_children():
        w.destroy()

def draw_2d_map(tab, matrix, bx, by, gx, gy):
    clear_tab(tab)
    plt.style.use('dark_background')
    fig = plt.figure(figsize=(6, 6), dpi=100)
    fig.patch.set_facecolor(BG_COLOR)
    ax = fig.add_subplot(111)
    ax.set_facecolor(BG_COLOR)
    
    xe, ye = np.linspace(0, bx, gx + 1), np.linspace(0, by, gy + 1)
    ax.pcolormesh(xe, ye, matrix, cmap='RdYlBu_r', edgecolors='#222222', linewidth=0.5)
    
    xc, yc = (xe[:-1] + xe[1:]) / 2, (ye[:-1] + ye[1:]) / 2
    for i in range(gy):
        for j in range(gx):
            t = ax.text(xc[j], yc[i], f"{matrix[i,j]:.3f}", ha="center", va="center", 
                        fontweight='bold', color="white", fontsize=8)
            t.set_path_effects([path_effects.withStroke(linewidth=2, foreground="black")])
    
    ax.set_aspect('equal')
    # Исправление ошибки FontProperties: передаем размер явно
    ax.set_xlabel("X (мм)", fontsize=9)
    ax.set_ylabel("Y (мм)", fontsize=9)
    
    canvas = FigureCanvasTkAgg(fig, master=tab)
    canvas.draw()
    canvas.get_tk_widget().pack(fill="both", expand=True)

def draw_3d_pro(tab, matrix, bx, by, gx, gy):
    """Продвинутая 3D карта с эффектом сглаживания и тенями"""
    clear_tab(tab)
    plt.style.use('dark_background')
    fig = plt.figure(figsize=(7, 7), dpi=100)
    fig.patch.set_facecolor(BG_COLOR)
    
    # Регистрация 3D осей
    from mpl_toolkits.mplot3d import Axes3D 
    ax = fig.add_subplot(111, projection='3d')
    ax.set_facecolor(BG_COLOR)
    
    # 1. МАТЕМАТИЧЕСКОЕ СГЛАЖИВАНИЕ (как в Plotly)
    x, y = np.linspace(0, bx, gx), np.linspace(0, by, gy)
    X, Y = np.meshgrid(x, y)
    # Оптимальная плотность для скорости (40x40 точек)
    x_f, y_f = np.linspace(0, bx, 40), np.linspace(0, by, 40)
    X_f, Y_f = np.meshgrid(x_f, y_f)
    Z_f = griddata((X.ravel(), Y.ravel()), matrix.ravel(), (X_f, Y_f), method='cubic')

    # 2. ИМИТАЦИЯ ОСВЕЩЕНИЯ (Объем и тени)
    ls = LightSource(azdeg=315, altdeg=45)
    # Используем RdYlBu_r для точного соответствия стилю Klipper
    rgb = ls.shade(Z_f, cmap=plt.get_cmap('RdYlBu_r'), vert_exag=0.1, blend_mode='soft')

    # 3. ОТРИСОВКА ПОВЕРХНОСТИ
    surf = ax.plot_surface(X_f, Y_f, Z_f, facecolors=rgb, rstride=1, cstride=1, 
                          antialiased=True, linewidth=0, shade=False)
    
    # Прозрачные панели осей
    ax.xaxis.set_pane_color((0,0,0,0))
    ax.yaxis.set_pane_color((0,0,0,0))
    ax.zaxis.set_pane_color((0,0,0,0))
    
    # Настройка осей (без передачи кортежей шрифтов)
    ax.set_xlabel('X', fontsize=8)
    ax.set_ylabel('Y', fontsize=8)
    ax.set_zlabel('Z', fontsize=8)
    
    ax.view_init(elev=30, azim=-135)
    ax.mouse_init() # Вращение мышью

    canvas = FigureCanvasTkAgg(fig, master=tab)
    canvas.draw()
    canvas.get_tk_widget().pack(fill="both", expand=True)