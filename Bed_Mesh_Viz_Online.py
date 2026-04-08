import streamlit as st
import plotly.graph_objects as go
import matplotlib.pyplot as plt
import numpy as np
import re

# Настройка страницы
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
        raw_nums = re.findall(r"[-+]?\d*\.\d+|\d+", data_input)
        # Если вставили лог Klipper, отсекаем первые технические цифры, если они не относятся к точкам
        # Но для простоты берем последние (grid_x * grid_y) чисел
        nums = [float(n) for n in raw_nums]
        
        total = grid_x * grid_y
        if len(nums) < total:
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