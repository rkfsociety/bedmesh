import streamlit as st
import plotly.graph_objects as go
import matplotlib.pyplot as plt
import matplotlib.patheffects as path_effects
import numpy as np
import re
import json

# Настройка страницы
<<<<<<< HEAD
st.set_page_config(page_title="Bed Mesh Master v4.0", layout="wide")
=======
st.set_page_config(page_title="Bed Mesh Master v3.9", layout="wide")
>>>>>>> c4ade77bd0e6495693ac81778f5bceb9309f9302

st.title("📏 Bed Mesh Visualizer")

# --- БОКОВАЯ ПАНЕЛЬ ---
st.sidebar.header("📂 Загрузка конфигурации")
uploaded_file = st.sidebar.file_uploader("Загрузить printer_mutable.cfg", type=['cfg', 'txt', 'conf'])

<<<<<<< HEAD
=======
# Переменные по умолчанию
>>>>>>> c4ade77bd0e6495693ac81778f5bceb9309f9302
default_vals = {
    "grid_x": 5, "grid_y": 5,
    "min_x": 10.0, "max_x": 240.0,
    "min_y": 10.0, "max_y": 240.0,
    "points": ""
}

if uploaded_file is not None:
    raw_content = uploaded_file.read().decode("utf-8")
<<<<<<< HEAD
    try:
        if raw_content.strip().startswith('{'):
            data = json.loads(raw_content) [cite: 1]
            mesh_data = data.get("bed_mesh default", {}) [cite: 1]
            if mesh_data:
                default_vals["grid_x"] = int(mesh_data.get("x_count", 5)) [cite: 1]
                default_vals["grid_y"] = int(mesh_data.get("y_count", 5)) [cite: 1]
                default_vals["min_x"] = float(mesh_data.get("min_x", 5)) [cite: 1]
                default_vals["max_x"] = float(mesh_data.get("max_x", 245)) [cite: 1]
                default_vals["min_y"] = float(mesh_data.get("min_y", 5)) [cite: 1]
                default_vals["max_y"] = float(mesh_data.get("max_y", 245)) [cite: 1]
                default_vals["points"] = mesh_data.get("points", "").strip() [cite: 1]
                st.sidebar.success("✅ Данные JSON загружены!")
        else:
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
bed_size_x = st.sidebar.number_input("Размер стола X", value=250)
bed_size_y = st.sidebar.number_input("Размер стола Y", value=250)

st.sidebar.header("2. Настройки сетки")
grid_x = st.sidebar.number_input("Точек по X", value=default_vals["grid_x"])
grid_y = st.sidebar.number_input("Точек по Y", value=default_vals["grid_y"])
min_x = st.sidebar.number_input("Min X", value=default_vals["min_x"])
max_x = st.sidebar.number_input("Max X", value=default_vals["max_x"])
min_y = st.sidebar.number_input("Min Y", value=default_vals["min_y"])
max_y = st.sidebar.number_input("Max Y", value=default_vals["max_y"])

origin_choice = st.sidebar.selectbox("Начало координат (0,0)", ["Левый-ближний угол", "Левый-дальний угол", "Правый-ближний угол", "Правый-дальний угол"])

# --- ОСНОВНАЯ ЧАСТЬ ---
data_input = st.text_area("Данные точек:", value=default_vals["points"], height=150)
=======
    
    try:
        # Проверка: является ли файл JSON (как в вашем случае)
        if raw_content.strip().startswith('{'):
            data = json.loads(raw_content)
            # Ищем данные в секции "bed_mesh default"
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
            # Если это обычный текстовый CFG Klipper
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
bed_size_x = st.sidebar.number_input("Размер стола X", value=250)
bed_size_y = st.sidebar.number_input("Размер стола Y", value=250)
screw_pitch = st.sidebar.selectbox("Шаг винтов", [0.7, 0.5, 0.8], format_func=lambda x: f"M4 (0.7мм)" if x==0.7 else f"M3 (0.5мм)")

st.sidebar.header("2. Настройки сетки")
grid_x = st.sidebar.number_input("Точек по X", value=default_vals["grid_x"])
grid_y = st.sidebar.number_input("Точек по Y", value=default_vals["grid_y"])
min_x = st.sidebar.number_input("Min X", value=default_vals["min_x"])
max_x = st.sidebar.number_input("Max X", value=default_vals["max_x"])
min_y = st.sidebar.number_input("Min Y", value=default_vals["min_y"])
max_y = st.sidebar.number_input("Max Y", value=default_vals["max_y"])

origin_choice = st.sidebar.selectbox("Начало координат (0,0)", ["Левый-ближний угол", "Левый-дальний угол", "Правый-ближний угол", "Правый-дальний угол"])

# --- ОСНОВНАЯ ЧАСТЬ ---
data_input = st.text_area("Данные точек (подтянутся из файла автоматически):", 
                         value=default_vals["points"], height=150)
>>>>>>> c4ade77bd0e6495693ac81778f5bceb9309f9302

if st.button("ПОСТРОИТЬ И АНАЛИЗИРОВАТЬ"):
    if data_input:
        raw_nums = re.findall(r"[-+]?\d*\.\d+|\d+", data_input)
        nums = [float(n) for n in raw_nums]
        total = grid_x * grid_y
        
        if len(nums) < total:
<<<<<<< HEAD
            st.error(f"Недостаточно данных: найдено {len(nums)} из {total}.")
        else:
            matrix = np.array(nums[-total:]).reshape((grid_y, grid_x))
=======
            st.error(f"Недостаточно данных: найдено {len(nums)} из {total}. Проверьте X и Y.")
        else:
            matrix = np.array(nums[-total:]).reshape((grid_y, grid_x))
            
>>>>>>> c4ade77bd0e6495693ac81778f5bceb9309f9302
            display_matrix = matrix.copy()
            if origin_choice == "Левый-дальний угол": display_matrix = np.flipud(display_matrix)
            elif origin_choice == "Правый-ближний угол": display_matrix = np.fliplr(display_matrix)
            elif origin_choice == "Правый-дальний угол": display_matrix = np.flipud(np.fliplr(display_matrix))

            x_edges = np.linspace(0, bed_size_x, grid_x + 1)
            y_edges = np.linspace(0, bed_size_y, grid_y + 1)
            x_centers = (x_edges[:-1] + x_edges[1:]) / 2
            y_centers = (y_edges[:-1] + y_edges[1:]) / 2

<<<<<<< HEAD
            t1, t2, t3 = st.tabs(["📊 3D Интерактив", "🗺️ 2D Карта", "🔧 Инструкция по выравниванию"])

            with t1:
                fig_3d = go.Figure(data=[go.Surface(x=np.linspace(min_x, max_x, grid_x), y=np.linspace(min_y, max_y, grid_y), z=display_matrix, colorscale='RdYlBu_r')])
=======
            t1, t2, t3 = st.tabs(["📊 3D Интерактив", "🗺️ 2D Карта", "🔧 Коррекция винтов"])

            with t1:
                fig_3d = go.Figure(data=[go.Surface(
                    x=np.linspace(min_x, max_x, grid_x), 
                    y=np.linspace(min_y, max_y, grid_y), 
                    z=display_matrix, colorscale='RdYlBu_r')])
>>>>>>> c4ade77bd0e6495693ac81778f5bceb9309f9302
                fig_3d.update_layout(scene=dict(xaxis_range=[0, bed_size_x], yaxis_range=[0, bed_size_y], aspectratio=dict(x=1, y=1, z=0.4)))
                st.plotly_chart(fig_3d, use_container_width=True)

            with t2:
                fig_2d, ax = plt.subplots(figsize=(10, 10))
                im = ax.pcolormesh(x_edges, y_edges, display_matrix, cmap='RdYlBu_r', edgecolors='black')
                for i in range(grid_y):
                    for j in range(grid_x):
                        txt = ax.text(x_centers[j], y_centers[i], f"{display_matrix[i, j]:.3f}", ha="center", va="center", fontweight='bold')
                        txt.set_path_effects([path_effects.withStroke(linewidth=2, foreground="white")])
                ax.set_xlim(0, bed_size_x); ax.set_ylim(0, bed_size_y); ax.set_aspect('equal')
                st.pyplot(fig_2d)

            with t3:
<<<<<<< HEAD
                st.header("⚙️ Выбор метода коррекции")
                method = st.radio("Что будем крутить?", ["Регулировочные винты стола", "Валы (моторы Z)"])
                
                if method == "Регулировочные винты стола":
                    screw_pitch = st.selectbox("Шаг винтов", [0.7, 0.5, 0.8], format_func=lambda x: f"M4 (0.7мм)" if x==0.7 else f"M3 (0.5мм)")
                    corners = {
                        "Передний-левый": display_matrix[0, 0], "Передний-правый": display_matrix[0, -1],
                        "Задний-левый": display_matrix[-1, 0], "Задний-правый": display_matrix[-1, -1]
                    }
                    base_val = min(corners.values())
                    c1, c2 = st.columns(2)
                    for idx, (name, val) in enumerate(corners.items()):
                        diff = val - base_val
                        with (c1 if idx < 2 else c2):
                            st.metric(name, f"{val:.3f} мм", f"{diff:+.3f} мм", delta_color="inverse")
                            if abs(diff) > 0.01:
                                st.write(f"🔧 Крутить: **{abs(diff)/screw_pitch:.2f}** об. ({'ВНИЗ' if diff > 0 else 'ВВЕРХ'})")
                
                else:
                    z_count = st.selectbox("Сколько независимых валов Z?", [2, 3, 4])
                    st.info(f"Расчет для {z_count} валов. Цель — привести все точки к среднему значению.")
                    
                    # Логика для валов зависит от их количества
                    if z_count == 2:
                        points_z = {"Левый вал (среднее по левой стороне)": np.mean(display_matrix[:, 0]), 
                                    "Правый вал (среднее по правой стороне)": np.mean(display_matrix[:, -1])}
                    elif z_count == 3:
                        points_z = {"Передний (центр)": display_matrix[0, grid_x//2], 
                                    "Задний левый": display_matrix[-1, 0], 
                                    "Задний правый": display_matrix[-1, -1]}
                    else: # 4 вала по углам
                        points_z = {"Передний-левый": display_matrix[0, 0], "Передний-правый": display_matrix[0, -1],
                                    "Задний-левый": display_matrix[-1, 0], "Задний-правый": display_matrix[-1, -1]}
                    
                    avg_z = np.mean(list(points_z.values()))
                    c1, c2 = st.columns(2)
                    for idx, (name, val) in enumerate(points_z.items()):
                        diff = val - avg_z
                        with (c1 if idx % 2 == 0 else c2):
                            st.metric(name, f"{val:.3f} мм", f"{diff:+.3f} мм", delta_color="inverse")
                            action = "ОПУСТИТЬ" if diff > 0 else "ПОДНЯТЬ"
                            st.write(f"⚙️ Сместить вал на **{abs(diff):.3f} мм** ({action})")
    else:
        st.info("Загрузите файл или введите данные.")
=======
                st.header("⚙️ Инструкция по винтам")
                # Углы берем из ориентированной матрицы
                corners = {
                    "Передний-левый": display_matrix[0, 0], "Передний-правый": display_matrix[0, -1],
                    "Задний-левый": display_matrix[-1, 0], "Задний-правый": display_matrix[-1, -1]
                }
                base_val = min(corners.values())
                c1, c2 = st.columns(2)
                for idx, (name, val) in enumerate(corners.items()):
                    diff = val - base_val
                    with (c1 if idx < 2 else c2):
                        st.metric(name, f"{val:.3f} мм", f"{diff:+.3f} мм", delta_color="inverse")
                        if abs(diff) > 0.01:
                            turns = abs(diff) / screw_pitch
                            direction = "ВНИЗ (затянуть)" if diff > 0 else "ВВЕРХ (отпустить)"
                            st.write(f"🔧 Крутить: **{turns:.2f}** об. ({direction})")
                        else:
                            st.write("✅ В уровне")
    else:
        st.info("Загрузите printer_mutable.cfg или вставьте данные точек вручную.")
>>>>>>> c4ade77bd0e6495693ac81778f5bceb9309f9302
