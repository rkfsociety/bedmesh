import streamlit as st
import plotly.graph_objects as go
import matplotlib.pyplot as plt
import matplotlib.cm as cm
import numpy as np
import re
import io

# Настройка страницы
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
        raw_nums = re.findall(r"[-+]?\d*\.\d+|\d+", data_input)
        nums = [float(n) for n in raw_nums]
        
        total = grid_x * grid_y
        if len(nums) < total:
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
