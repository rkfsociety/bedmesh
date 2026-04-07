import streamlit as st
import matplotlib.pyplot as plt
import numpy as np
import re

# Настройка страницы
st.set_page_config(page_title="Bed Mesh Visualizer Online", layout="centered")

st.title("🌐 Bed Mesh Visualizer Online")
st.markdown("Вставьте данные калибровки стола из консоли принтера (Klipper/Marlin).")

# Боковая панель с настройками
st.sidebar.header("Настройки сетки")
grid_x = st.sidebar.number_input("Точек по X", min_value=2, max_value=20, value=5)
grid_y = st.sidebar.number_input("Точек по Y", min_value=2, max_value=20, value=5)

# Поле ввода данных
data_input = st.text_area("Данные калибровки:", height=250, placeholder="1.643, 1.236, 1.044...")

if st.button("ВИЗУАЛИЗИРОВАТЬ 3D"):
    if data_input:
        # Парсинг чисел
        raw_nums = re.findall(r"[-+]?\d*\.\d+|\d+", data_input)
        nums = [float(n) for n in raw_nums]
        
        total_points = grid_x * grid_y
        
        if len(nums) < total_points:
            st.error(f"Ошибка: Нужно {total_points} точек для сетки {grid_x}x{grid_y}, а найдено только {len(nums)}.")
        else:
            # Создание матрицы
            matrix = np.array(nums[:total_points]).reshape((grid_y, grid_x))
            
            # Построение графика
            fig = plt.figure(figsize=(10, 7))
            ax = fig.add_subplot(111, projection='3d')
            
            y, x = np.indices(matrix.shape)
            
            surf = ax.plot_surface(x, y, matrix, cmap='RdYlBu_r', edgecolor='black', 
                                   linewidth=0.5, antialiased=True, alpha=0.8)
            
            fig.colorbar(surf, shrink=0.5, aspect=10, label='Z (мм)')
            ax.set_title(f"Сетка: {grid_x} x {grid_y}")
            ax.set_xlabel("X")
            ax.set_ylabel("Y")
            
            # Отображение в Streamlit
            st.pyplot(fig)
    else:
        st.warning("Пожалуйста, вставьте данные.")