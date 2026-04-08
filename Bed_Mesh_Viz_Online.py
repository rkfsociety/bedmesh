import streamlit as st
import plotly.graph_objects as go
import matplotlib.pyplot as plt
import matplotlib.patheffects as path_effects
import numpy as np
import re

# Настройка страницы
st.set_page_config(page_title="Bed Mesh Professional v3.6", layout="wide")

st.title("📏 Bed Mesh Visualizer (Perfect Grid)")

# --- БОКОВАЯ ПАНЕЛЬ ---
st.sidebar.header("1. Физические размеры стола (мм)")
bed_size_x = st.sidebar.number_input("Размер стола по X", value=250)
bed_size_y = st.sidebar.number_input("Размер стола по Y", value=250)

st.sidebar.header("2. Границы сетки Mesh (мм)")
# ВАЖНО: Эти координаты используются для 3D, в 2D они показывают отступы
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
            # Матрица данных: первая точка — это минимальные X и Y
            matrix = np.array(nums[-total:]).reshape((grid_y, grid_x))
            
            # --- РАСЧЕТ ОДИНАКОВЫХ КВАДРАТОВ НА ВЕСЬ СТОЛ ---
            # Создаем сетку, которая делит весь стол на равные сектора
            x_edges = np.linspace(0, bed_size_x, grid_x + 1)
            y_edges = np.linspace(0, bed_size_y, grid_y + 1)
            
            # Точки замера (для 3D и текста) будут в центрах этих секторов
            x_centers = (x_edges[:-1] + x_edges[1:]) / 2
            y_centers = (y_edges[:-1] + y_edges[1:]) / 2

            # Логика ориентации для отображения
            display_matrix = matrix.copy()
            if origin_choice == "Левый-ближний угол":
                pass # Стандарт: Y растет вверх, X вправо
            elif origin_choice == "Левый-дальний угол":
                display_matrix = np.flipud(display_matrix)
            elif origin_choice == "Правый-ближний угол":
                display_matrix = np.fliplr(display_matrix)
            elif origin_choice == "Правый-дальний угол":
                display_matrix = np.flipud(np.fliplr(display_matrix))

            tab1, tab2 = st.tabs(["📊 3D Вид", "🗺️ 2D Карта (Равные квадраты)"])

            with tab1:
                # 3D вид всё же используем с реальными координатами замера
                # Чтобы показать реальную область зондирования
                real_x = np.linspace(min_x, max_x, grid_x)
                real_y = np.linspace(min_y, max_y, grid_y)
                
                fig_3d = go.Figure(data=[go.Surface(
                    x=real_x, y=real_y, z=display_matrix,
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
                fig_2d, ax = plt.subplots(figsize=(10, 10))
                
                # Рисуем сетку pcolormesh по РАВНЫМ краям
                im = ax.pcolormesh(x_edges, y_edges, display_matrix, 
                                 cmap='RdYlBu_r', edgecolors='black', linewidth=1)
                
                # Добавляем текст в центры равных секторов
                for i in range(grid_y):
                    for j in range(grid_x):
                        val = display_matrix[i, j]
                        txt = ax.text(x_centers[j], y_centers[i], f"{val:.3f}", 
                                     ha="center", va="center", color='black', 
                                     fontsize=9, fontweight='bold')
                        txt.set_path_effects([path_effects.withStroke(linewidth=2, foreground="white")])

                ax.set_xlim(0, bed_size_x)
                ax.set_ylim(0, bed_size_y)
                ax.set_aspect('equal')
                
                # Разметка осей по границам ячеек
                ax.set_xticks(x_edges)
                ax.set_yticks(y_edges)
                ax.grid(color='black', linestyle='-', linewidth=0.5, alpha=0.5)
                
                ax.set_title(f"2D Карта стола {bed_size_x}x{bed_size_y} мм (Равные сектора)")
                ax.set_xlabel("X (мм)")
                ax.set_ylabel("Y (мм)")
                
                fig_2d.colorbar(im, label='Отклонение Z (мм)')
                st.pyplot(fig_2d)
    else:
        st.info("Вставьте данные...")