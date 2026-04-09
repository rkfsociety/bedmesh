import streamlit as st
import plotly.graph_objects as go
import matplotlib.pyplot as plt
import matplotlib.patheffects as path_effects
import numpy as np
import re
import json

# Настройка страницы
st.set_page_config(page_title="Bed Mesh Visualizer Pro v4.6", layout="wide")

st.title("📏 Bed Mesh Visualizer Pro v4.6 (Online)")

# --- БОКОВАЯ ПАНЕЛЬ ---
st.sidebar.header("📂 Загрузка данных")
uploaded_file = st.sidebar.file_uploader("Загрузить printer_mutable.cfg", type=['cfg', 'txt', 'conf', 'json'])

default_vals = {
    "grid_x": 5, "grid_y": 5,
    "min_x": 10.0, "max_x": 240.0,
    "min_y": 10.0, "max_y": 240.0,
    "points": ""
}

if uploaded_file is not None:
    raw_content = uploaded_file.read().decode("utf-8")
    try:
        if raw_content.strip().startswith('{'):
            data = json.loads(raw_content)
            mesh_data = data.get("bed_mesh default", {})
            if mesh_data:
                default_vals.update({
                    "grid_x": int(mesh_data.get("x_count", 5)),
                    "grid_y": int(mesh_data.get("y_count", 5)),
                    "min_x": float(mesh_data.get("min_x", 5)),
                    "max_x": float(mesh_data.get("max_x", 245)),
                    "min_y": float(mesh_data.get("min_y", 5)),
                    "max_y": float(mesh_data.get("max_y", 245)),
                    "points": mesh_data.get("points", "").strip()
                })
        else:
            def find_val(pattern, text, default):
                match = re.search(pattern, text)
                return match.group(1) if match else default
            
            default_vals.update({
                "grid_x": int(find_val(r"x_count\s*=\s*(\d+)", raw_content, 5)),
                "grid_y": int(find_val(r"y_count\s*=\s*(\d+)", raw_content, 5)),
                "min_x": float(find_val(r"min_x\s*=\s*([\d.]+)", raw_content, 5)),
                "max_x": float(find_val(r"max_x\s*=\s*([\d.]+)", raw_content, 245)),
                "min_y": float(find_val(r"min_y\s*=\s*([\d.]+)", raw_content, 5)),
                "max_y": float(find_val(r"max_y\s*=\s*([\d.]+)", raw_content, 245))
            })
            points_match = re.search(r"points\s*=\s*([\s\S]+?)(?=\n\s*[a-zA-Z_]+\s*=|\[|\Z)", raw_content)
            if points_match: default_vals["points"] = points_match.group(1).strip()
            
        st.sidebar.success("✅ Данные загружены!")
    except:
        st.sidebar.error("Ошибка парсинга файла.")

st.sidebar.header("1. Параметры стола")
bed_x = st.sidebar.number_input("Размер X (мм)", value=250)
bed_y = st.sidebar.number_input("Размер Y (мм)", value=250)
screw_pitch = st.sidebar.selectbox("Шаг винтов", [0.7, 0.5, 0.8], format_func=lambda x: f"M4 (0.7мм)" if x==0.7 else f"M3 (0.5мм)")

st.sidebar.header("2. Настройки сетки")
grid_x = st.sidebar.number_input("Точек X", value=default_vals["grid_x"])
grid_y = st.sidebar.number_input("Точек Y", value=default_vals["grid_y"])
mx_val, Mx_val = st.sidebar.number_input("Min X mesh", value=default_vals["min_x"]), st.sidebar.number_input("Max X mesh", value=default_vals["max_x"])
my_val, My_val = st.sidebar.number_input("Min Y mesh", value=default_vals["min_y"]), st.sidebar.number_input("Max Y mesh", value=default_vals["max_y"])

# --- ВВОД ДАННЫХ ---
data_input = st.text_area("Данные точек (points):", value=default_vals["points"], height=150)

if st.button("ПОСТРОИТЬ КАРТУ"):
    if data_input:
        raw_nums = re.findall(r"[-+]?\d*\.\d+|\d+", data_input)
        nums = [float(n) for n in raw_nums]
        total = grid_x * grid_y
        
        if len(nums) < total:
            st.error(f"Нужно {total} точек, найдено {len(nums)}.")
        else:
            matrix = np.array(nums[:total]).reshape((grid_y, grid_x))
            
            # Логика змейки
            for i in range(len(matrix)):
                if i % 2 != 0: matrix[i] = matrix[i][::-1]
            
            # --- РАСЧЕТ ОТКЛОНЕНИЯ ---
            max_val = np.max(matrix)
            min_val = np.min(matrix)
            variance = max_val - min_val
            
            # Отображение метрик
            col1, col2, col3 = st.columns(3)
            col1.metric("Отклонение (Variance)", f"{variance:.3f} мм", delta=f"{variance:.3f}", delta_color="inverse")
            col2.metric("Максимум (Max Z)", f"{max_val:.3f} мм")
            col3.metric("Минимум (Min Z)", f"{min_val:.3f} мм")

            tab1, tab2 = st.tabs(["📊 3D Интерактив", "🗺️ 2D Карта и Винты"])

            with tab1:
                x_coords = np.linspace(mx_val, Mx_val, grid_x)
                y_coords = np.linspace(my_val, My_val, grid_y)
                fig_3d = go.Figure(data=[go.Surface(x=x_coords, y=y_coords, z=matrix, colorscale='RdYlBu_r')])
                fig_3d.update_layout(
                    scene=dict(xaxis_title='X (мм)', yaxis_title='Y (мм)', zaxis_title='Z (мм)',
                               xaxis=dict(range=[0, bed_x]), yaxis=dict(range=[0, bed_y])),
                    width=800, height=800
                )
                st.plotly_chart(fig_3d, use_container_width=True)

            with tab2:
                fig_2d, ax = plt.subplots(figsize=(8, 8))
                x_edges = np.linspace(0, bed_x, grid_x + 1)
                y_edges = np.linspace(0, bed_y, grid_y + 1)
                im = ax.pcolormesh(x_edges, y_edges, matrix, cmap='RdYlBu_r', edgecolors='black', linewidth=1)
                
                x_centers = (x_edges[:-1] + x_edges[1:]) / 2
                y_centers = (y_edges[:-1] + y_edges[1:]) / 2
                for i in range(grid_y):
                    for j in range(grid_x):
                        txt = ax.text(x_centers[j], y_centers[i], f"{matrix[i,j]:.3f}", ha="center", va="center", fontweight='bold')
                        txt.set_path_effects([path_effects.withStroke(linewidth=2, foreground="white")])

                ax.set_xlim(0, bed_x); ax.set_ylim(0, bed_y); ax.set_aspect('equal')
                
                # Расчет винтов
                corners = {"ПЛ": matrix[0,0], "ПП": matrix[0,-1], "ЗЛ": matrix[-1,0], "ЗП": matrix[-1,-1]}
                low = min(corners.values())
                instr = "\n".join([f"{k}: {v-low:+.3f}мм ({(v-low)/screw_pitch:.2f} об. {'ВНИЗ' if v-low>0 else 'ОК'})" for k,v in corners.items()])
                plt.gcf().text(0.12, 0.02, f"Винты (отн. низшего):\n{instr}", fontsize=10, bbox=dict(facecolor='white', alpha=0.8))
                
                fig_2d.colorbar(im, label="Z (мм)")
                st.pyplot(fig_2d)