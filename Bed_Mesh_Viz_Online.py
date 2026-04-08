import streamlit as st
import plotly.graph_objects as go
import matplotlib.pyplot as plt
<<<<<<< HEAD
=======
import matplotlib.cm as cm
>>>>>>> 2c114ee1a58101c1f7a8a98ccd41ea44c6c49470
import numpy as np
import re
import io

# Настройка страницы
<<<<<<< HEAD
st.set_page_config(page_title="Bed Mesh Professional", layout="wide")

st.title("📏 Bed Mesh Visualizer с координатами")

# --- БОКОВАЯ ПАНЕЛЬ ---
st.sidebar.header("1. Физические размеры (мм)")
bed_size_x = st.sidebar.number_input("Размер стола X", value=250)
bed_size_y = st.sidebar.number_input("Размер стола Y", value=250)

st.sidebar.header("2. Границы сетки (Mesh)")
min_x = st.sidebar.number_input("Min X", value=5)
max_x = st.sidebar.number_input("Max X", value=245)
min_y = st.sidebar.number_input("Min Y", value=5)
max_y = st.sidebar.number_input("Max Y", value=245)

st.sidebar.header("3. Сетка (Точки)")
grid_x = st.sidebar.number_input("Точек по X", min_value=2, value=5)
grid_y = st.sidebar.number_input("Точек по Y", min_value=2, value=5)

origin_choice = st.sidebar.selectbox(
    "Начало координат (0,0)",
    ["Левый-ближний угол", "Левый-дальний угол", "Правый-ближний угол", "Правый-дальний угол"]
)

# --- ОСНОВНАЯ ЧАСТЬ ---
data_input = st.text_area("Вставьте данные (JSON или список чисел):", height=200, 
                         placeholder='Например: "points": "1.07, 0.58..."')

if st.button("ПОСТРОИТЬ КАРТУ С КООРДИНАТАМИ"):
    if data_input:
        # Извлекаем все числа
=======
st.set_page_config(page_title="Bed Mesh Dual View", layout="wide")

st.title("🔄 Двойной Bed Mesh Visualizer (3D & 2D)")

# --- БОКОВАЯ ПАНЕЛЬ (НАСТРОЙКИ) ---
st.sidebar.header("⚙️ Настройки")

# Выбор сетки
grid_x = st.sidebar.number_input("Точек по X", min_value=2, max_value=20, value=5)
grid_y = st.sidebar.number_input("Точек по Y", min_value=2, max_value=20, value=5)

# ВСПЛЫВАЮЩИЙ СПИСОК ВЫБОРА УГЛА (0,0)
origin_choice = st.sidebar.selectbox(
    "Где находится начало координат (0,0)?",
    [
        "Левый-ближний угол", 
        "Левый-дальний угол", 
        "Правый-ближний угол", 
        "Правый-дальний угол"
    ]
)

# Чекбокс для сглаживания 3D
smooth_3d = st.sidebar.checkbox("Включить сглаживание 3D", value=True)

# --- ОСНОВНАЯ ЧАСТЬ ---
data_input = st.text_area("Вставьте данные калибровки (консоль принтера):", height=150, placeholder="0.150, 0.025, -0.010...")

if st.button("ПОСТРОИТЬ ОБЕ КАРТЫ"):
    if data_input:
        # Извлекаем числа
>>>>>>> 2c114ee1a58101c1f7a8a98ccd41ea44c6c49470
        raw_nums = re.findall(r"[-+]?\d*\.\d+|\d+", data_input)
        # Если вставили лог Klipper, отсекаем первые технические цифры, если они не относятся к точкам
        # Но для простоты берем последние (grid_x * grid_y) чисел
        nums = [float(n) for n in raw_nums]
        
        total = grid_x * grid_y
        if len(nums) < total:
<<<<<<< HEAD
            st.error(f"Найдено {len(nums)} чисел, а нужно {total}. Проверьте настройки сетки.")
        else:
            # Берем нужную часть данных (обычно последние значения в блоке JSON)
            points = np.array(nums[-total:]).reshape((grid_y, grid_x))
            
            # Ориентация
            if origin_choice == "Левый-ближний угол":
                points = np.flipud(points)
            elif origin_choice == "Правый-ближний угол":
                points = np.flipud(np.fliplr(points))
            elif origin_choice == "Правый-дальний угол":
                points = np.fliplr(points)

            # Создаем массивы координат в мм
            x_range = np.linspace(min_x, max_x, grid_x)
            y_range = np.linspace(min_y, max_y, grid_y)
            X, Y = np.meshgrid(x_range, y_range)

            tab1, tab2 = st.tabs(["📊 3D Вид", "🗺️ 2D Карта"])

            with tab1:
                fig_3d = go.Figure(data=[go.Surface(
                    x=x_range, y=y_range, z=points,
                    colorscale='RdYlBu_r',
                    colorbar=dict(title='Z (мм)')
                )])
                
                fig_3d.update_layout(
                    scene=dict(
                        xaxis=dict(title='X (мм)', range=[0, bed_size_x]),
                        yaxis=dict(title='Y (мм)', range=[0, bed_size_y]),
                        zaxis=dict(title='Z (мм)'),
                        aspectmode='manual',
                        aspectratio=dict(x=1, y=1, z=0.4)
                    ),
                    margin=dict(l=0, r=0, b=0, t=40)
                )
                st.plotly_chart(fig_3d, use_container_width=True)

            with tab2:
                fig_2d, ax = plt.subplots(figsize=(10, 8))
                # Центрируем данные в границах min/max на фоне всего стола
                im = ax.imshow(points, extent=[min_x, max_x, min_y, max_y], 
                               cmap='RdYlBu_r', interpolation='bicubic', origin='lower')
                
                # Добавляем цифры
                for i, py in enumerate(y_range):
                    for j, px in enumerate(x_range):
                        val = points[i, j]
                        ax.text(px, py, f"{val:.3f}", ha="center", va="center", 
                                color="black" if abs(val) < 0.1 else "white", fontsize=8, fontweight='bold')

                ax.set_xlim(0, bed_size_x)
                ax.set_ylim(0, bed_size_y)
                ax.set_title("2D Карта в масштабе стола (мм)")
                ax.set_xlabel("X (мм)")
                ax.set_ylabel("Y (мм)")
                ax.grid(True, linestyle='--', alpha=0.6)
                fig_2d.colorbar(im, label='Z (мм)')
                st.pyplot(fig_2d)
    else:
        st.info("Вставьте блок данных из конфигурации Klipper.")
=======
            st.error(f"Ошибка! Для сетки {grid_x}x{grid_y} нужно {total} точек, найдено только {len(nums)}.")
        else:
            # Создаем базовую матрицу (Y - строки, X - столбцы)
            matrix = np.array(nums[:total]).reshape((grid_y, grid_x))
            
            # --- ЛОГИКА ОРИЕНТАЦИИ (ОТЗЕРКАЛИВАНИЕ) ---
            # Применяем трансформации, чтобы горб был там, где он на столе
            if origin_choice == "Левый-ближний угол":
                # Klipper standard: first row is Y-max
                matrix = np.flipud(matrix) 
            elif origin_choice == "Правый-ближний угол":
                matrix = np.flipud(np.fliplr(matrix))
            elif origin_choice == "Правый-дальний угол":
                matrix = np.fliplr(matrix)
            # "Левый-дальний" остается без изменений

            # Создаем вкладки для переключения видов
            tab1, tab2 = st.tabs(["📊 3D Интерактивный вид", "🗺️ 2D Вид сверху (со значениями)"])

            # --- ТАБ 1: 3D ИНТЕРАКТИВНЫЙ ВИД (PLOTLY) ---
            with tab1:
                # Включаем сглаживание
                z_smooth = 'best' if smooth_3d else False
                
                fig_3d = go.Figure(data=[go.Surface(
                    z=matrix,
                    colorscale='RdYlBu_r',  # Klipper Style
                    reversescale=False,
                    colorbar=dict(title='Z (мм)', tickformat=".3f"),
                    # Настройка сглаживания
                    contours_z=dict(show=True, usecolormap=True, highlightcolor="limegreen", project_z=True),
                    opacity=0.9
                )])

                fig_3d.update_layout(
                    title=f'3D Карта: {grid_x}x{grid_y} ({origin_choice})',
                    scene=dict(
                        xaxis_title='Ось X (точки)',
                        yaxis_title='Ось Y (точки)',
                        zaxis_title='Высота Z (мм)',
                        aspectratio=dict(x=1, y=1, z=0.5) # Приплюснем по Z
                    ),
                    width=900,
                    height=800,
                    margin=dict(l=0, r=0, b=0, t=40)
                )

                st.plotly_chart(fig_3d, use_container_width=True)

            # --- ТАБ 2: 2D ВИД СВЕРХУ (MATPLOTLIB) ---
            with tab2:
                # Создаем график matplotlib
                fig_2d, ax = plt.figure(figsize=(10, 8), dpi=100), plt.gca()
                
                # 'bicubic' делает плавные переходы цветов, 'nearest' - четкие квадраты
                im = ax.imshow(matrix, cmap='RdYlBu_r', interpolation='bicubic')
                
                # Добавляем цветовую панель
                fig_2d.colorbar(im, label='Отклонение Z (мм)')
                
                # Настройка осей
                ax.set_title(f"2D Карта (Вид сверху, 0,0: {origin_choice})")
                ax.set_xticks(np.arange(grid_x))
                ax.set_yticks(np.arange(grid_y))
                
                # Подписи осей X и Y (как точки калибровки)
                ax.set_xticklabels([f"X{i}" for i in range(grid_x)])
                ax.set_yticklabels([f"Y{grid_y-1-i}" for i in range(grid_y)]) # Y переворачиваем для наглядности
                
                ax.set_xlabel("Ось X")
                ax.set_ylabel("Ось Y")

                # --- ДОБАВЛЯЕМ ЦИФРЫ ВНУТРЬ КВАДРАТОВ ---
                # Определяем пороговое значение для смены цвета текста (чтобы было видно на темном)
                # Вычисляем среднее, чтобы понять, какой текст лучше
                thresh = (matrix.max() + matrix.min()) / 2
                
                for i in range(grid_y):
                    for j in range(grid_x):
                        # Цвет текста зависит от высоты: белый на темном, черный на светлом
                        color = "white" if matrix[i, j] < thresh else "black"
                        
                        # Рисуем текст
                        text = ax.text(j, i, f"{matrix[i, j]:.3f}",
                                      ha="center", va="center", color=color,
                                      fontweight='bold', fontsize=8)

                # Сетка
                ax.set_xticks(np.arange(grid_x+1)-.5, minor=True)
                ax.set_yticks(np.arange(grid_y+1)-.5, minor=True)
                ax.grid(which="minor", color="black", linestyle='-', linewidth=0.5)
                ax.tick_params(which="minor", bottom=False, left=False)

                # Вывод в Streamlit
                st.pyplot(fig_2d)
    else:
        st.warning("Пожалуйста, вставьте данные.")
>>>>>>> 2c114ee1a58101c1f7a8a98ccd41ea44c6c49470
