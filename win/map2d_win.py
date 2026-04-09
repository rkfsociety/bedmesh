import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import numpy as np

def draw_2d_map(parent, matrix, bed_x, bed_y, gx, gy):
    """
    Отрисовка четкой 2D карты: каждый квадрат соответствует точке замера.
    """
    # Очистка старого графика
    for w in parent.winfo_children():
        w.destroy()

    # Создание фигуры
    fig, ax = plt.subplots(figsize=(8, 6), dpi=100)
    fig.patch.set_facecolor('#2b2b2b')
    ax.set_facecolor('#2b2b2b')
    
    # interpolation='nearest' убирает размытие между точками
    # origin='lower' ставит 0,0 в левый нижний угол
    im = ax.imshow(matrix, cmap='viridis', interpolation='nearest', origin='lower',
                   extent=[0, bed_x, 0, bed_y])
    
    # Добавление цветовой шкалы
    cbar = plt.colorbar(im, ax=ax)
    cbar.set_label('Отклонение (мм)', color='white')
    cbar.ax.yaxis.set_tick_params(color='white', labelcolor='white')
    
    ax.set_title("Карта высот (Точки замера)", color='white', pad=20)
    ax.set_xlabel("X (мм)", color='white')
    ax.set_ylabel("Y (мм)", color='white')
    ax.tick_params(colors='white')
    
    # Настройка сетки, чтобы четко видеть границы квадратов
    ax.set_xticks(np.linspace(0, bed_x, gx + 1), minor=True)
    ax.set_yticks(np.linspace(0, bed_y, gy + 1), minor=True)
    ax.grid(which="minor", color="black", linestyle='-', linewidth=0.5)
    
    # Убираем основные линии сетки, оставляем только границы квадратов
    ax.grid(which="major", visible=False)

    # Интеграция в Tkinter
    canvas = FigureCanvasTkAgg(fig, master=parent)
    canvas.draw()
    canvas.get_tk_widget().pack(fill="both", expand=True)