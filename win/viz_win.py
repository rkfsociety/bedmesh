import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.patheffects as path_effects
import numpy as np

BG_COLOR = "#1a1a1a"

def clear_tab(tab):
    """Очищает вкладку перед новой отрисовкой"""
    for w in tab.winfo_children():
        w.destroy()

def draw_2d_map(tab, matrix, bx, by, gx, gy):
    """
    Отрисовывает чистую 2D карту с мягкой интерполяцией,
    правильно центрированными цифрами и чистыми осями.
    """
    clear_tab(tab)
    plt.style.use('dark_background')
    
    # Создаем фигуру с темным фоном
    fig = plt.figure(figsize=(6, 6), dpi=100)
    fig.patch.set_facecolor(BG_COLOR)
    ax = fig.add_subplot(111)
    ax.set_facecolor(BG_COLOR)
    
    # 1. Мягкая интерполяция (Heatmap)
    # extent=[0, bx, 0, by] — задает диапазон осей (например, 0-250)
    # origin='lower' — ставит точку (0,0) в левый нижний угол
    im = ax.imshow(matrix, cmap='RdYlBu_r', origin='lower', 
                   extent=[0, bx, 0, by], interpolation='quadric')
    
    # 2. Расчет центров квадратов для правильного размещения текста
    # Границы квадратов:
    xe = np.linspace(0, bx, gx)
    ye = np.linspace(0, by, gy)
    
    # Центры квадратов (середины между границами):
    dx = (bx / gx) / 2
    dy = (by / gy) / 2
    
    centers_x = xe + dx
    centers_y = ye + dy
    
    # 3. Добавление числовых значений В ЦЕНТРЫ
    # Находим минимальное и максимальное значения для автовыбора цвета текста
    z_min, z_max = matrix.min(), matrix.max()
    threshold = (z_max + z_min) / 2
    
    for i in range(gy):
        for j in range(gx):
            val = matrix[i, j]
            
            # Если точка "высокая" (красная), текст делаем черным для читаемости,
            # если "низкая" (синяя) — белым.
            text_color = "black" if val > threshold else "white"
            
            # Помещаем текст точно в центр квадрата:
            t = ax.text(centers_x[j], centers_y[i], f"{val:+.3f}", 
                        ha="center", va="center", # Выравнивание внутри текста
                        fontweight='bold', color=text_color, fontsize=8)
            
            # Если текст белый, добавляем черную обводку для контраста
            if text_color == "white":
                t.set_path_effects([path_effects.withStroke(linewidth=1.5, foreground="black")])
    
    # 4. Настройка осей (ЧИСТЫЕ)
    ax.set_aspect('equal')
    ax.set_xlabel("X (мм)", fontsize=9, color="#aaaaaa")
    ax.set_ylabel("Y (мм)", fontsize=9, color="#aaaaaa")
    
    # Убираем старые, грязные тики
    ax.tick_params(axis='both', which='both', length=0) # Скрываем "засечки"
    
    # Устанавливаем только чистые границы (0, 62.5, 125 и т.д.)
    ax.set_xticks(xe)
    ax.set_yticks(ye)
    
    # Цвет текста координат
    ax.tick_params(axis='x', colors='#aaaaaa', labelsize=8)
    ax.tick_params(axis='y', colors='#aaaaaa', labelsize=8)
    
    # Легкая сетка поверх градиента, чтобы видеть границы
    ax.grid(color='#ffffff', linestyle='--', linewidth=0.5, alpha=0.15)
    
    # Убираем рамку вокруг графика
    for spine in ax.spines.values():
        spine.set_visible(False)

    # 5. Отрисовка на холсте
    canvas = FigureCanvasTkAgg(fig, master=tab)
    canvas.draw()
    canvas.get_tk_widget().pack(fill="both", expand=True)