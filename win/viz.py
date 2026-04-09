import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.patheffects as path_effects
import numpy as np
from mpl_toolkits.mplot3d import Axes3D # Обязательно для 3D
import styles

# Цвета фона вкладок (синхронизация с CustomTkinter)
BG_COLOR_HEX = "#1a1a1a"

def clear_tab(tab):
    """Очищает вкладку от старых графиков"""
    for w in tab.winfo_children():
        w.destroy()

def draw_2d_map(tab, matrix, bx, by, gx, gy):
    """Отрисовка 2D карты (Тепловая карта с цифрами)"""
    clear_tab(tab)
    
    # Настройка стиля под темную тему
    plt.style.use('dark_background')
    fig = plt.figure(figsize=(6, 6), dpi=100)
    fig.patch.set_facecolor(BG_COLOR_HEX)
    
    ax = fig.add_subplot(111)
    ax.set_facecolor(BG_COLOR_HEX)
    
    # Сетка координат
    xe = np.linspace(0, bx, gx + 1)
    ye = np.linspace(0, by, gy + 1)
    
    # Сама тепловая карта
    im = ax.pcolormesh(xe, ye, matrix, cmap='RdYlBu_r', edgecolors='black', linewidth=0.5)
    
    # Текст с высотами в центрах ячеек
    xc, yc = (xe[:-1] + xe[1:]) / 2, (ye[:-1] + ye[1:]) / 2
    for i in range(gy):
        for j in range(gx):
            val = matrix[i,j]
            # Белый текст с черной обводкой для читаемости
            t = ax.text(xc[j], yc[i], f"{val:.3f}", ha="center", va="center", 
                        fontweight='bold', color="white", fontsize=8)
            t.set_path_effects([path_effects.withStroke(linewidth=2, foreground="black")])
    
    # Оформление осей (убираем лишние рамки)
    ax.set_aspect('equal')
    ax.set_xlabel("X (мм)", font=styles.FONTS["micro"])
    ax.set_ylabel("Y (мм)", font=styles.FONTS["micro"])
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    
    # Встраивание в Tkinter
    canvas = FigureCanvasTkAgg(fig, master=tab)
    canvas.draw()
    canvas.get_tk_widget().pack(fill="both", expand=True)

def draw_3d_klipper_style(tab, matrix, bx, by, gx, gy):
    """Отрисовка 3D карты в стиле Klipper (интерактивная, яркая, с сеткой)"""
    clear_tab(tab)
    
    # Стиль
    plt.style.use('dark_background')
    fig = plt.figure(figsize=(7, 7), dpi=100)
    fig.patch.set_facecolor(BG_COLOR_HEX)
    
    # Создаем 3D оси
    ax = fig.add_subplot(111, projection='3d')
    ax.set_facecolor(BG_COLOR_HEX)
    
    # Данные для поверхности
    X, Y = np.meshgrid(np.linspace(0, bx, gx), np.linspace(0, by, gy))
    
    # --- СТИЛИЗАЦИЯ ПОД KLIPPER ---
    # 1. cmap='jet' (яркая сине-красная, как в старом Plotly/Fluidd)
    # 2. edgecolors='black', lw=0.5 (накладывает черную сетку рельефа)
    # 3. antialiased=True (сглаживание)
    surf = ax.plot_surface(X, Y, matrix, cmap='jet', edgecolor='black', 
                          linewidth=0.3, antialiased=True, alpha=0.9)
    
    # Настройка осей и фона (делаем минималистично)
    # Убираем серые панели фона
    ax.xaxis.set_pane_color((0,0,0,0))
    ax.yaxis.set_pane_color((0,0,0,0))
    ax.zaxis.set_pane_color((0,0,0,0))
    
    # Делаем сетку осей тоньше
    ax.xaxis._axinfo["grid"]['color'] =  styles.COLORS["dark"]["text_dim"]
    ax.yaxis._axinfo["grid"]['color'] =  styles.COLORS["dark"]["text_dim"]
    ax.zaxis._axinfo["grid"]['color'] =  styles.COLORS["dark"]["text_dim"]

    # Подписи
    ax.set_xlabel('X', color=styles.COLORS["dark"]["text_dim"], font=styles.FONTS["micro"])
    ax.set_ylabel('Y', color=styles.COLORS["dark"]["text_dim"], font=styles.FONTS["micro"])
    ax.set_zlabel('Z', color=styles.COLORS["dark"]["text_dim"], font=styles.FONTS["micro"])
    
    # Устанавливаем начальный угол обзора
    ax.view_init(elev=30, azim=-120)

    # --- ИНТЕРАКТИВНОСТЬ ---
    # Позволяет крутить график мышью, масштабировать колесиком
    fig.canvas.mpl_connect('button_press_event', ax._button_press)
    fig.canvas.mpl_connect('button_release_event', ax._button_release)
    fig.canvas.mpl_connect('motion_notify_event', ax._on_move)
    # Заставляем Matplotlib перерисовывать график мгновенно при движении мыши
    ax.mouse_init()

    # Встраивание
    canvas = FigureCanvasTkAgg(fig, master=tab)
    canvas.draw()
    canvas.get_tk_widget().pack(fill="both", expand=True)