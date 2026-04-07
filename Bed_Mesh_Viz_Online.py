import streamlit as st
import plotly.graph_objects as go
import numpy as np
import re

# Настройка страницы
st.set_page_config(page_title="Bed Mesh Visualizer", layout="wide")

st.title("🔄 Интерактивный Bed Mesh Visualizer")

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

# Чекбокс для сглаживания
smooth = st.sidebar.checkbox("Включить сглаживание (Klipper Style)", value=True)

# --- ОСНОВНАЯ ЧАСТЬ ---
data_input = st.text_area("Вставьте данные калибровки:", height=200, placeholder="0.150, 0.025, -0.010...")

if st.button("ПОСТРОИТЬ 3D КАРТУ"):
    if data_input:
        # Извлекаем числа
        raw_nums = re.findall(r"[-+]?\d*\.\d+|\d+", data_input)
        nums = [float(n) for n in raw_nums]
        
        total = grid_x * grid_y
        if len(nums) < total:
            st.error(f"Ошибка! Для сетки {grid_x}x{grid_y} нужно {total} точек, найдено только {len(nums)}.")
        else:
            # Создаем матрицу
            matrix = np.array(nums[:total]).reshape((grid_y, grid_x))
            
            # --- ЛОГИКА ОРИЕНТАЦИИ (ОТЗЕРКАЛИВАНИЕ) ---
            if origin_choice == "Левый-ближний угол":
                matrix = np.flipud(matrix) 
            elif origin_choice == "Правый-ближний угол":
                matrix = np.flipud(np.fliplr(matrix))
            elif origin_choice == "Правый-дальний угол":
                matrix = np.fliplr(matrix)
            # "Левый-дальний" остается без изменений (стандарт для reshape)

            # --- ПОСТРОЕНИЕ ГРАФИКА ---
            fig = go.Figure(data=[go.Surface(
                z=matrix,
                colorscale='RdYlBu_r',
                # Включаем сглаживание, если выбран чекбокс
                contours_z=dict(show=True, usecolormap=True, highlightcolor="limegreen", project_z=True),
                surfacecolor=matrix,
                reversescale=False,
                connectgaps=True
            )])

            # Настройка сглаживания в Plotly
            if smooth:
                fig.update_traces(contours_z=dict(show=True, usecolormap=True, project_z=True))
            
            fig.update_layout(
                title=f'Визуализация: {grid_x}x{grid_y} ({origin_choice})',
                scene=dict(
                    xaxis_title='Ось X',
                    yaxis_title='Ось Y',
                    zaxis_title='Высота Z (мм)',
                    aspectratio=dict(x=1, y=1, z=0.5)
                ),
                width=900,
                height=800
            )

            st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("Поле пустое. Скопируйте данные из консоли принтера.")
