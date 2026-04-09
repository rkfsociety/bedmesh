import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import numpy as np
import matplotlib.colors as mcolors

def draw_2d_map(parent, matrix, bed_x, bed_y, gx, gy):
    """
    Отрисовка 2D карты:
    - Раскраска относительно среднего значения (Mean).
    - Красный: ниже среднего, Зеленый: выше среднего.
    - Без заголовка.
    """
    for w in parent.winfo_children():
        w.destroy()

    # Создаем фигуру с темным фоном под интерфейс
    fig, ax = plt.subplots(figsize=(8, 6), dpi=100)
    fig.patch.set_facecolor('#2b2b2b')
    ax.set_facecolor('#2b2b2b')
    
    # Считаем среднее значение матрицы
    avg_val = np.mean(matrix)
    v_min = matrix.min()
    v_max = matrix.max()
    
    # Гарантируем, что диапазон не нулевой для корректной работы палитры
    if v_min == v_max:
        v_min -= 0.1
        v_max += 0.1

    # Устанавливаем среднее значение как центр палитры
    # RdYlGn: Red (низ) -> Yellow (центр/среднее) -> Green (верх)
    norm = mcolors.TwoSlopeNorm(vcenter=avg_val, vmin=v_min, vmax=v_max)
    
    im = ax.imshow(matrix, cmap='RdYlGn', interpolation='nearest', origin='lower',
                   extent=[0, bed_x, 0, bed_y], norm=norm, alpha=0.9)
    
    # Добавление числовых значений в центры квадратов
    step_x = bed_x / gx
    step_y = bed_y / gy

    for y in range(gy):
        for x in range(gx):
            val = matrix[y, x]
            pos_x = (x * step_x) + (step_x / 2)
            pos_y = (y * step_y) + (step_y / 2)
            
            # Текст всегда черный для пастельной палитры
            ax.text(pos_x, pos_y, f"{val:+.3f}", 
                    ha="center", va="center", 
                    color="black", fontsize=9, fontweight='bold')

    # Настройка цветовой шкалы (Colorbar)
    cbar = plt.colorbar(im, ax=ax)
    cbar.set_label('Отклонение (мм)', color='white')
    cbar.ax.yaxis.set_tick_params(color='white', labelcolor='white')
    
    # Убрали ax.set_title, оставляем только подписи осей
    ax.set_xlabel("X (мм)", color='white')
    ax.set_ylabel("Y (мм)", color='white')
    ax.tick_params(colors='white')
    
    # Настройка тонкой сетки
    ax.set_xticks(np.linspace(0, bed_x, gx + 1), minor=True)
    ax.set_yticks(np.linspace(0, bed_y, gy + 1), minor=True)
    ax.grid(which="minor", color="black", linestyle='-', linewidth=0.5, alpha=0.15)
    ax.grid(which="major", visible=False)

    # Интеграция в Tkinter
    canvas = FigureCanvasTkAgg(fig, master=parent)
    canvas.draw()
    canvas.get_tk_widget().pack(fill="both", expand=True)