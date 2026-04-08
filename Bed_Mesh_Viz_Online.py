import streamlit as st
import plotly.graph_objects as go
import matplotlib.pyplot as plt
import matplotlib.patheffects as path_effects
import numpy as np
import re

# Настройка страницы
st.set_page_config(page_title="Bed Mesh Professional v3.4", layout="wide")

st.title("📏 Bed Mesh Visualizer (Full Bed View)")

# --- БОКОВАЯ ПАНЕЛЬ ---
st.sidebar.header("1. Физические размеры стола (мм)")
bed_size_x = st.sidebar.number_input("Размер стола по X", value=250)
bed_size_y = st.sidebar.number_input("Размер стола по Y", value=250)

st.sidebar.header("2. Границы сетки Mesh (мм)")
min_x = st.sidebar.number_input("Min X", value=5)
max_x = st.sidebar.number_input("Max X", value=245)
min_y = st.sidebar.number_input("Min Y", value=5)
max_y = st.sidebar.number_input("Max Y", value=245)

st.sidebar.header("3. Сетка (Точки)")
grid_x = st.sidebar.number_input("Кол-во точек по X", min_value=2, value=5)
grid_y = st.sidebar.number_input("Кол-во точек по Y", min_value=2, value=5)

origin_choice = st.sidebar.selectbox(
    "Где на принтере X0 Y0?",
    ["Левый-ближний угол", "Левый-дальний угол", "Правый-ближний угол", "Правый-дальний угол"]
)

# --- ВВОД ДАННЫХ ---
data_input = st.text_area("Вставьте данные (JSON, лог или числа):", height=150)

if st.button("ПОСТРОИТЬ КАРТУ"):
    if data_input:
        raw_nums = re.findall(r"[-+]?\d*\.\d+|\d+", data_input)
        nums = [float(n) for n in raw_nums]
        
        total = grid_x * grid_y
        if len(nums) < total:
            st.error(f"Нужно {total} точек, найдено {len(nums)}")
        else:
            # Матрица данных (Klipper обычно выдает Y строк, X столбцов)
            matrix = np.array(nums[-total:]).reshape((grid_y, grid_x))
            
            # Логика ориентации
            if origin_choice == "Левый-ближний угол":
                matrix = np.flipud(matrix)
            elif origin_choice == "Правый-ближний угол":
                matrix = np.flipud(np.fliplr(matrix))
            elif origin_choice == "Правый-дальний угол":
                matrix = np.fliplr(matrix)

            # Координаты точек замера
            x_coords = np.linspace(min_x, max_x, grid_x)
            y_coords = np.linspace(min_y, max_y, grid_y)

            tab1, tab2 = st.tabs(["📊 3D Вид", "🗺️ 2D Карта (Весь стол)"])

            with tab1:
                fig_3d = go.Figure(data=[go.Surface(
                    x=x_coords, y=y_coords, z=matrix,
                    colorscale='RdYlBu_r',
                    colorbar=dict(title='Z (мм)', tickformat=".3f")
                )])
                fig_3d.update_layout(
                    scene=dict(
                        xaxis=dict(title='X (мм)', range=[0, bed_size_x]),
                        yaxis=dict(title='Y (мм)', range=[0, bed_size_y]),
                        zaxis=dict(title='Z (мм)'),
                        aspectratio=dict(x=1, y=1, z=0.4)
                    ),
                    margin=dict(l=0, r=0, b=0, t=40)
                )
                st.plotly_chart(fig_3d, use_container_width=True)

            with tab2:
                fig_2d, ax = plt.subplots(figsize=(12, 10))
                
                # Используем imshow на ВЕСЬ размер стола (0 до bed_size)
                # Это создаст одинаковые квадраты
                im = ax.imshow(matrix, 
                               extent=[0, bed_size_x, 0, bed_size_y], 
                               cmap='RdYlBu_r', 
                               interpolation='nearest', # Четкие квадраты одинакового размера
                               origin='lower')
                
                # Добавляем цифры. Координаты текста теперь распределены по всему полю
                text_x = np.linspace(bed_size_x/(grid_x*2), bed_size_x - bed_size_x/(grid_x*2), grid_x)
                text_y = np.linspace(bed_size_y/(grid_y*2), bed_size_y - bed_size_y/(grid_y*2), grid_y)

                for i in range(grid_y):
                    for j in range(grid_x):
                        val = matrix[i, j]
                        txt = ax.text(text_x[j], text_y[i], f"{val:.3f}", 
                                     ha="center", va="center", color='black', 
                                     fontsize=10, fontweight='bold')
                        txt.set_path_effects([path_effects.withStroke(linewidth=2, foreground="white")])

                # Настройка сетки и осей
                ax.set_xticks(np.linspace(0, bed_size_x, grid_x + 1))
                ax.set_yticks(np.linspace(0, bed_size_y, grid_y + 1))
                ax.grid(color='black', linestyle='-', linewidth=0.8)
                
                ax.set_title(f"2D Карта стола {bed_size_x}x{bed_size_y} мм")
                ax.set_xlabel("X (мм)")
                ax.set_ylabel("Y (мм)")
                
                fig_2d.colorbar(im, label='Отклонение Z (мм)')
                st.pyplot(fig_2d)
    else:
        st.info("Вставьте данные...")