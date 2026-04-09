import streamlit as st
import plotly.graph_objects as go
import matplotlib.pyplot as plt
import matplotlib.patheffects as path_effects
import numpy as np
import re
import json

# Настройка страницы
st.set_page_config(page_title="Bed Mesh Visualizer Pro v4.5", layout="wide")

st.title("📏 Bed Mesh Visualizer Pro v4.5 (Online)")

# --- БОКОВАЯ ПАНЕЛЬ ---
st.sidebar.header("📂 Загрузка данных")
uploaded_file = st.sidebar.file_uploader("Загрузить printer_mutable.cfg", type=['cfg', 'txt', 'conf', 'json'])

# Переменные по умолчанию
default_vals = {
    "grid_x": 5, "grid_y": 5,
    "min_x": 10.0, "max_x": 240.0,
    "min_y": 10.0, "max_y": 240.0,
    "points": ""
}

if uploaded_file is not None:
    raw_content = uploaded_file.read().decode("utf-8")
    try:
        # Пытаемся распарсить как JSON (printer_mutable.cfg)
        if raw_content.strip().startswith('{'):
            data = json.loads(raw_content)
            mesh_data = data.get("bed_mesh default", {})
            if mesh_data:
                default_vals["grid_x"] = int(mesh_data.get("x_count", 5))
                default_vals["grid_y"] = int(mesh_data.get("y_count", 5))
                default_vals["min_x"] = float(mesh_data.get("min_x", 5))
                default_vals["max_x"] = float(mesh_data.get("max_x", 245))
                default_vals["min_y"] = float(mesh_data.get("min_y", 5))
                default_vals["max_y"] = float(mesh_data.get("max_y", 245))
                default_vals["points"] = mesh_data.get("points", "").strip()
                st.sidebar.success("✅ Данные JSON загружены!")
        else:
            # Обычный Klipper CFG
            def find_val(pattern, text, default):
                match = re.search(pattern, text)
                return match.group(1) if match else default
            
            default_vals["grid_x"] = int(find_val(r"x_count\s*=\s*(\d+)", raw_content, 5))
            default_vals["grid_y"] = int(find_val(r"y_count\s*=\s*(\d+)", raw_content, 5))
            default_vals["min_x"] = float(find_val(r"min_x\s*=\s*([\d.]+)", raw_content, 5))
            default_vals["max_x"] = float(find_val(r"max_x\s*=\s*([\d.]+)", raw_content, 245))
            default_vals["min_y"] = float(find_val(r"min_y\s*=\s*([\d.]+)", raw_content, 5))
            default_vals["max_y"] = float(find_val(r"max_y\s*=\s*([\d.]+)", raw_content, 245))
            
            points_match = re.search(r"points\s*=\s*([\s\S]+?)(?=\n\s*[a-zA-Z_]+\s*=|\[|\Z)", raw_content)
            if points_match:
                default_vals["points"] = points_match.group(1).strip()
            st.sidebar.success("✅ Данные CFG загружены!")
    except Exception as e:
        st.sidebar.error(f"Ошибка чтения: {e}")

st.sidebar.header("1. Параметры стола")
bed_x = st.sidebar.number_input("Размер стола X (мм)", value=250)
bed_y = st.sidebar.number_input("Размер стола Y (мм)", value=250)
screw_pitch = st.sidebar.selectbox("Шаг винтов", [0.7, 0.5, 0.8], format_func=lambda x: f"M4 (0.7мм)" if x==0.7 else f"M3 (0.5мм)")

st.sidebar.header("2. Настройки сетки")
grid_x = st.sidebar.number_input("Точек X", value=default_vals["grid_x"])
grid_y = st.sidebar.number_input("Точек Y", value=default_vals["grid_y"])
min_x_val = st.sidebar.number_input("Min X mesh", value=default_vals["min_x"])
max_x_val = st.sidebar.number_input("Max X mesh", value=default_vals["max_x"])
min_y_val = st.sidebar.number_input("Min Y mesh", value=default_vals["min_y"])
max_y_val = st.sidebar.number_input("Max Y mesh", value=default_vals["max_y"])

# --- ВВОД ДАННЫХ ---
data_input = st.text_area("Данные точек (points):", value=default_vals["points"], height=150)

if st.button("ПОСТРОИТЬ КАРТУ"):
    if data_input:
        # Очищаем данные: берем только числа из строки points
        raw_nums = re.findall(r"[-+]?\d*\.\d+|\d+", data_input)
        nums = [float(n) for n in raw_nums]
        
        total_needed = grid_x * grid_y
        if len(nums) < total_needed:
            st.error(f"Нужно {total_needed} точек, найдено {len(nums)}. Проверьте X/Y.")
        else:
            # Формируем матрицу из первых gx*gy найденных чисел
            matrix = np.array(nums[:total_needed]).reshape((grid_y, grid_x))
            
            # --- ЛОГИКА ЗМЕЙКИ (v4.5) ---
            # Каждая нечетная строка в Klipper (1, 3, 5...) записана в обратном порядке
            for i in range(len(matrix)):
                if i % 2 != 0:
                    matrix[i] = matrix[i][::-1]
            
            # Координаты для визуализации
            x_coords = np.linspace(min_x_val, max_x_val, grid_x)
            y_coords = np.linspace(min_y_val, max_y_val, grid_y)
            
            tab1, tab2 = st.tabs(["📊 3D Интерактив", "🗺️ 2D Карта и Винты"])

            with tab1:
                fig_3d = go.Figure(data=[go.Surface(
                    x=x_coords, y=y_coords, z=matrix,
                    colorscale='RdYlBu_r',
                    colorbar=dict(title="Z (мм)")
                )])
                fig_3d.update_layout(
                    title="3D Вид стола",
                    scene=dict(
                        xaxis=dict(title='X (мм)', range=[0, bed_x]),
                        yaxis=dict(title='Y (мм)', range=[0, bed_y]),
                        zaxis=dict(title='Z (мм)'),
                        aspectratio=dict(x=1, y=1, z=0.4)
                    ),
                    width=800, height=800
                )
                st.plotly_chart(fig_3d, use_container_width=True)

            with tab2:
                # Настройка квадратного графика Matplotlib
                fig_2d, ax = plt.subplots(figsize=(8, 8))
                
                # Сетка для pcolormesh (границы квадратов по всему столу)
                x_edges = np.linspace(0, bed_x, grid_x + 1)
                y_edges = np.linspace(0, bed_y, grid_y + 1)
                x_centers = (x_edges[:-1] + x_edges[1:]) / 2
                y_centers = (y_edges[:-1] + y_edges[1:]) / 2

                im = ax.pcolormesh(x_edges, y_edges, matrix, cmap='RdYlBu_r', edgecolors='black', linewidth=1)
                
                # Текст строго по центрам квадратов
                for i in range(grid_y):
                    for j in range(grid_x):
                        txt = ax.text(x_centers[j], y_centers[i], f"{matrix[i,j]:.3f}", 
                                     ha="center", va="center", fontweight='bold', fontsize=9)
                        txt.set_path_effects([path_effects.withStroke(linewidth=2, foreground="white")])

                ax.set_xlim(0, bed_x)
                ax.set_ylim(0, bed_y)
                ax.set_aspect('equal')
                ax.set_xlabel("X (мм)")
                ax.set_ylabel("Y (мм)")
                ax.set_title("2D Карта (Центрированная)")
                
                # Инструкция по винтам
                corners = {"ПЛ": matrix[0,0], "ПП": matrix[0,-1], "ЗЛ": matrix[-1,0], "ЗП": matrix[-1,-1]}
                base = min(corners.values())
                instr = "\n".join([f"{k}: {v-base:+.3f}мм ({(v-base)/screw_pitch:.2f} об. {'ВНИЗ' if v-base>0 else 'ОК'})" for k,v in corners.items()])
                plt.gcf().text(0.12, 0.02, f"Винты (отн. низшего):\n{instr}", fontsize=10, bbox=dict(facecolor='white', alpha=0.8))
                
                fig_2d.colorbar(im, label="Z (мм)")
                st.pyplot(fig_2d)
    else:
        st.info("Загрузите файл или вставьте данные точек вручную.")