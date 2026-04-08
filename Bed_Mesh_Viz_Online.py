import streamlit as st
import plotly.graph_objects as go
import matplotlib.pyplot as plt
import matplotlib.patheffects as path_effects
import numpy as np
import re

# Настройка страницы
st.set_page_config(page_title="Bed Mesh Master v3.7", layout="wide")

st.title("📏 Bed Mesh Visualizer + Инструкции по правке")

# --- БОКОВАЯ ПАНЕЛЬ ---
st.sidebar.header("1. Физические размеры стола (мм)")
bed_size_x = st.sidebar.number_input("Размер стола по X", value=250)
bed_size_y = st.sidebar.number_input("Размер стола по Y", value=250)

st.sidebar.header("2. Параметры винтов")
screw_pitch = st.sidebar.selectbox("Шаг резьбы винтов", [0.7, 0.5, 0.8], format_func=lambda x: f"M4 (0.7мм)" if x==0.7 else f"M3 (0.5мм)" if x==0.5 else f"M5 (0.8мм)")

st.sidebar.header("3. Сетка и границы")
min_x = st.sidebar.number_input("Min X", value=5)
max_x = st.sidebar.number_input("Max X", value=245)
min_y = st.sidebar.number_input("Min Y", value=5)
max_y = st.sidebar.number_input("Max Y", value=245)
grid_x = st.sidebar.number_input("Точек по X", min_value=2, value=5)
grid_y = st.sidebar.number_input("Точек по Y", min_value=2, value=5)

origin_choice = st.sidebar.selectbox(
    "Начало координат (0,0)",
    ["Левый-ближний угол", "Левый-дальний угол", "Правый-ближний угол", "Правый-дальний угол"]
)

# --- ВВОД ДАННЫХ ---
data_input = st.text_area("Вставьте данные (JSON, лог или числа):", height=150)

if st.button("АНАЛИЗИРОВАТЬ И ПОСТРОИТЬ"):
    if data_input:
        raw_nums = re.findall(r"[-+]?\d*\.\d+|\d+", data_input)
        nums = [float(n) for n in raw_nums]
        
        total = grid_x * grid_y
        if len(nums) < total:
            st.error(f"Нужно {total} точек, найдено {len(nums)}")
        else:
            matrix = np.array(nums[-total:]).reshape((grid_y, grid_x))
            
            # Логика ориентации
            display_matrix = matrix.copy()
            if origin_choice == "Левый-дальний угол":
                display_matrix = np.flipud(display_matrix)
            elif origin_choice == "Правый-ближний угол":
                display_matrix = np.fliplr(display_matrix)
            elif origin_choice == "Правый-дальний угол":
                display_matrix = np.flipud(np.fliplr(display_matrix))

            # Координаты
            x_edges = np.linspace(0, bed_size_x, grid_x + 1)
            y_edges = np.linspace(0, bed_size_y, grid_y + 1)
            x_centers = (x_edges[:-1] + x_edges[1:]) / 2
            y_centers = (y_edges[:-1] + y_edges[1:]) / 2

            tab1, tab2, tab3 = st.tabs(["📊 3D Вид", "🗺️ 2D Карта", "🔧 Инструкция по исправлению"])

            with tab1:
                real_x = np.linspace(min_x, max_x, grid_x)
                real_y = np.linspace(min_y, max_y, grid_y)
                fig_3d = go.Figure(data=[go.Surface(x=real_x, y=real_y, z=display_matrix, colorscale='RdYlBu_r')])
                fig_3d.update_layout(scene=dict(xaxis_range=[0, bed_size_x], yaxis_range=[0, bed_size_y], aspectratio=dict(x=1, y=1, z=0.4)))
                st.plotly_chart(fig_3d, use_container_width=True)

            with tab2:
                fig_2d, ax = plt.subplots(figsize=(10, 10))
                im = ax.pcolormesh(x_edges, y_edges, display_matrix, cmap='RdYlBu_r', edgecolors='black')
                for i in range(grid_y):
                    for j in range(grid_x):
                        txt = ax.text(x_centers[j], y_centers[i], f"{display_matrix[i, j]:.3f}", ha="center", va="center", fontweight='bold')
                        txt.set_path_effects([path_effects.withStroke(linewidth=2, foreground="white")])
                ax.set_xlim(0, bed_size_x); ax.set_ylim(0, bed_size_y); ax.set_aspect('equal')
                st.pyplot(fig_2d)

            with tab3:
                st.header("🛠️ Рекомендации по настройке винтов")
                
                # Извлекаем значения углов
                # Ближний левый [0,0], Ближний правый [0, -1], Дальний левый [-1, 0], Дальний правый [-1, -1]
                # ВАЖНО: берем из display_matrix, так как она уже ориентирована как стол
                corners = {
                    "Ближний левый (Front-Left)": display_matrix[0, 0],
                    "Ближний правый (Front-Right)": display_matrix[0, -1],
                    "Дальний левый (Back-Left)": display_matrix[-1, 0],
                    "Дальний правый (Back-Right)": display_matrix[-1, -1]
                }
                
                # Базовая точка (самая низкая, её не трогаем, остальные подтягиваем к ней)
                target_val = min(corners.values())
                
                col1, col2 = st.columns(2)
                
                for idx, (name, val) in enumerate(corners.items()):
                    diff = val - target_val
                    with (col1 if idx < 2 else col2):
                        st.subheader(name)
                        if diff == 0:
                            st.success("✅ Базовая точка (идеально)")
                        else:
                            turns = diff / screw_pitch
                            direction = "ПО часовой стрелке" if diff > 0 else "ПРОТИВ часовой стрелки"
                            action = "ОПУСТИТЬ" if diff > 0 else "ПОДНЯТЬ"
                            
                            st.error(f"Отклонение: **{diff:+.3f} мм**")
                            st.write(f"👉 Нужно **{action}** угол.")
                            st.info(f"Крутить: **{abs(turns):.2f}** оборота ({direction})")
                
                st.warning("⚠️ Примечание: Расчет сделан исходя из того, что затягивание винта (по часовой) опускает стол. Если у вас наоборот — смените направление.")

    else:
        st.info("Вставьте данные...")