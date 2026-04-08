import streamlit as st
import plotly.graph_objects as go
import matplotlib.pyplot as plt
import matplotlib.patheffects as path_effects
import numpy as np
import re

# Настройка страницы
st.set_page_config(page_title="Bed Mesh Professional v3.3", layout="wide")

st.title("📏 Bed Mesh Visualizer Pro")

# --- БОКОВАЯ ПАНЕЛЬ ---
st.sidebar.header("1. Физические размеры стола (мм)")
bed_size_x = st.sidebar.number_input("Размер стола по X", value=250)
bed_size_y = st.sidebar.number_input("Размер стола по Y", value=250)

st.sidebar.header("2. Границы сетки Mesh (мм)")
min_x = st.sidebar.number_input("Min X (начало)", value=5)
max_x = st.sidebar.number_input("Max X (конец)", value=245)
min_y = st.sidebar.number_input("Min Y (начало)", value=5)
max_y = st.sidebar.number_input("Max Y (конец)", value=245)

st.sidebar.header("3. Сетка (Точки)")
grid_x = st.sidebar.number_input("Кол-во точек по X", min_value=2, value=5)
grid_y = st.sidebar.number_input("Кол-во точек по Y", min_value=2, value=5)

origin_choice = st.sidebar.selectbox(
    "Где на принтере X0 Y0?",
    ["Левый-ближний угол", "Левый-дальний угол", "Правый-ближний угол", "Правый-дальний угол"]
)

st.sidebar.header("4. Визуализация")
smooth_3d = st.sidebar.checkbox("Сглаживание 3D (Klipper Style)", value=True)

# --- ВВОД ДАННЫХ ---
data_input = st.text_area("Вставьте данные (JSON, лог консоли или список чисел):", height=200, 
                         placeholder='Пример: "points": "1.079, 0.581, 0.254..."')

if st.button("ПОСТРОИТЬ КАРТУ"):
    if data_input:
        # Извлекаем все числа из текста
        raw_nums = re.findall(r"[-+]?\d*\.\d+|\d+", data_input)
        nums = [float(n) for n in raw_nums]
        
        total = grid_x * grid_y
        if len(nums) < total:
            st.error(f"Найдено {len(nums)} чисел, а для сетки {grid_x}x{grid_y} нужно {total}. Проверьте настройки X и Y.")
        else:
            # Берем последние (total) чисел, это обычно сами точки в логе
            matrix = np.array(nums[-total:]).reshape((grid_y, grid_x))
            
            # --- ЛОГИКА ОРИЕНТАЦИИ ---
            if origin_choice == "Левый-ближний угол":
                matrix = np.flipud(matrix)
            elif origin_choice == "Правый-ближний угол":
                matrix = np.flipud(np.fliplr(matrix))
            elif origin_choice == "Правый-дальний угол":
                matrix = np.fliplr(matrix)
            # "Левый-дальний" остается как есть

            # Генерируем реальные координаты точек в мм
            x_coords = np.linspace(min_x, max_x, grid_x)
            y_coords = np.linspace(min_y, max_y, grid_y)
            X_mesh, Y_mesh = np.meshgrid(x_coords, y_coords)

            tab1, tab2 = st.tabs(["📊 3D Интерактив", "🗺️ 2D Карта (Миллиметры)"])

            # --- ТАБ 1: 3D PLOTLY ---
            with tab1:
                fig_3d = go.Figure(data=[go.Surface(
                    x=x_coords, y=y_coords, z=matrix,
                    colorscale='RdYlBu_r',
                    colorbar=dict(title='Z (мм)', tickformat=".3f"),
                    contours_z=dict(show=True, usecolormap=True, highlightcolor="limegreen", project_z=True)
                )])
                
                fig_3d.update_layout(
                    title=f'3D Рельеф стола ({grid_x}x{grid_y})',
                    scene=dict(
                        xaxis=dict(title='X (мм)', range=[0, bed_size_x]),
                        yaxis=dict(title='Y (мм)', range=[0, bed_size_y]),
                        zaxis=dict(title='Z (мм)'),
                        aspectmode='manual',
                        aspectratio=dict(x=1, y=1, z=0.4)
                    ),
                    width=900,
                    height=800,
                    margin=dict(l=0, r=0, b=0, t=40)
                )
                if smooth_3d:
                    fig_3d.update_traces(connectgaps=True)

                st.plotly_chart(fig_3d, use_container_width=True)

            # --- ТАБ 2: 2D MATPLOTLIB (ИСПРАВЛЕННЫЙ ТЕКСТ) ---
            with tab2:
                fig_2d, ax = plt.subplots(figsize=(12, 10))
                
                # Рисуем карту с четкими границами
                im = ax.pcolormesh(X_mesh, Y_mesh, matrix, cmap='RdYlBu_r', edgecolors='black', linewidth=0.5, shading='auto')
                
                # Добавляем цифры в центр каждого замера
                for i in range(grid_y):
                    for j in range(grid_x):
                        cx = x_coords[j]
                        cy = y_coords[i]
                        val = matrix[i, j]
                        
                        # Рисуем текст с эффектом белой обводки
                        txt = ax.text(cx, cy, f"{val:.3f}", 
                                     ha="center", va="center", 
                                     color='black', fontsize=9, fontweight='bold')
                        
                        txt.set_path_effects([
                            path_effects.withStroke(linewidth=2, foreground="white")
                        ])

                # Настройка осей и границ
                ax.set_xlim(0, bed_size_x)
                ax.set_ylim(0, bed_size_y)
                ax.set_aspect('equal')
                ax.set_title(f"Точки замера на поверхности стола (0,0: {origin_choice})")
                ax.set_xlabel("X (мм)")
                ax.set_ylabel("Y (мм)")
                
                # Показываем сетку
                ax.set_xticks(x_coords, minor=True)
                ax.set_yticks(y_coords, minor=True)
                ax.grid(which="minor", color="white", linestyle='-', linewidth=0.2, alpha=0.3)
                
                fig_2d.colorbar(im, label='Отклонение Z (мм)', fraction=0.046, pad=0.04)
                st.pyplot(fig_2d)
    else:
        st.info("Ожидание данных для визуализации...")