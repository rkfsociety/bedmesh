import streamlit as st
import plotly.graph_objects as go
import matplotlib.pyplot as plt
import matplotlib.patheffects as path_effects
import numpy as np
import re
import json

# Настройка страницы
st.set_page_config(page_title="Bed Mesh Visualizer Pro v4.9", layout="wide")

st.title("📏 Bed Mesh Visualizer Pro v4.9 (Multi-Z Support)")

# --- БОКОВАЯ ПАНЕЛЬ ---
st.sidebar.header("📂 Загрузка данных")
uploaded_file = st.sidebar.file_uploader("Загрузить printer_mutable.cfg", type=['cfg', 'txt', 'conf', 'json'])

default_vals = {"grid_x": 5, "grid_y": 5, "min_x": 10.0, "max_x": 240.0, "min_y": 10.0, "max_y": 240.0, "points": ""}

if uploaded_file is not None:
    raw_content = uploaded_file.read().decode("utf-8")
    try:
        if raw_content.strip().startswith('{'):
            data = json.loads(raw_content)
            mesh_data = data.get("bed_mesh default", {})
            if mesh_data:
                default_vals.update({
                    "grid_x": int(mesh_data.get("x_count", 5)), "grid_y": int(mesh_data.get("y_count", 5)),
                    "min_x": float(mesh_data.get("min_x", 5)), "max_x": float(mesh_data.get("max_x", 245)),
                    "min_y": float(mesh_data.get("min_y", 5)), "max_y": float(mesh_data.get("max_y", 245)),
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
            pts = re.search(r"points\s*=\s*([\s\S]+?)(?=\n\s*[a-zA-Z_]+\s*=|\[|\Z)", raw_content)
            if pts: default_vals["points"] = pts.group(1).strip()
    except: st.sidebar.error("Ошибка парсинга.")

st.sidebar.header("1. Конфигурация Z (Валы)")
z_type = st.sidebar.radio("Система валов:", ["2 вала (Л/П)", "3 вала (2 спереди, 1 сзади)"])
screw_pitch = st.sidebar.selectbox("Шаг винта", [0.7, 0.5, 0.8], index=0)

st.sidebar.header("2. Геометрия")
bed_x = st.sidebar.number_input("Размер X (мм)", value=250)
bed_y = st.sidebar.number_input("Размер Y (мм)", value=250)
grid_x = st.sidebar.number_input("Точек X", value=default_vals["grid_x"])
grid_y = st.sidebar.number_input("Точек Y", value=default_vals["grid_y"])
mx_val, Mx_val = st.sidebar.number_input("Min X mesh", value=default_vals["min_x"]), st.sidebar.number_input("Max X mesh", value=default_vals["max_x"])
my_val, My_val = st.sidebar.number_input("Min Y mesh", value=default_vals["min_y"]), st.sidebar.number_input("Max Y mesh", value=default_vals["max_y"])

data_input = st.text_area("Данные точек (points):", value=default_vals["points"], height=150)

if st.button("🚀 ПОСТРОИТЬ КАРТУ", use_container_width=True):
    if data_input:
        raw_nums = re.findall(r"[-+]?\d*\.\d+|\d+", data_input)
        nums = [float(n) for n in raw_nums]
        if len(nums) < grid_x * grid_y:
            st.error("Недостаточно точек!")
        else:
            matrix = np.array(nums[:grid_x*grid_y]).reshape((grid_y, grid_x))
            for i in range(len(matrix)):
                if i % 2 != 0: matrix[i] = matrix[i][::-1]
            
            variance = np.max(matrix) - np.min(matrix)
            m1, m2, m3 = st.columns(3)
            m1.metric("Variance", f"{variance:.3f} мм")
            m2.metric("Max Z", f"{np.max(matrix):.3f} мм")
            m3.metric("Min Z", f"{np.min(matrix):.3f} мм")

            tab1, tab2 = st.tabs(["📊 3D Интерактив", "🗺️ 2D Карта"])
            with tab1:
                fig_3d = go.Figure(data=[go.Surface(x=np.linspace(mx_val, Mx_val, grid_x), y=np.linspace(my_val, My_val, grid_y), z=matrix, colorscale='RdYlBu_r')])
                fig_3d.update_layout(scene=dict(xaxis=dict(range=[0, bed_x]), yaxis=dict(range=[0, bed_y])), width=800, height=800)
                st.plotly_chart(fig_3d, use_container_width=True)

            with tab2:
                fig_2d, ax = plt.subplots(figsize=(8, 8))
                x_edges = np.linspace(0, bed_x, grid_x + 1); y_edges = np.linspace(0, bed_y, grid_y + 1)
                im = ax.pcolormesh(x_edges, y_edges, matrix, cmap='RdYlBu_r', edgecolors='black', linewidth=1)
                xc, yc = (x_edges[:-1] + x_edges[1:]) / 2, (y_edges[:-1] + y_edges[1:]) / 2
                for i in range(grid_y):
                    for j in range(grid_x):
                        txt = ax.text(xc[j], yc[i], f"{matrix[i,j]:.3f}", ha="center", va="center", fontweight='bold')
                        txt.set_path_effects([path_effects.withStroke(linewidth=2, foreground="white")])
                ax.set_aspect('equal'); fig_2d.colorbar(im); st.pyplot(fig_2d)

            # --- ЛОГИКА ВЫРАВНИВАНИЯ ВАЛОВ ---
            st.divider()
            st.subheader(f"⚖️ Выравнивание валов ({z_type})")
            
            if "2 вала" in z_type:
                l_avg, r_avg = np.mean(matrix[:, 0]), np.mean(matrix[:, -1])
                diff = l_avg - r_avg
                c1, c2 = st.columns(2)
                c1.write(f"Слева: `{l_avg:.3f}` | Справа: `{r_avg:.3f}`")
                side = "ЛЕВЫЙ" if diff > 0 else "ПРАВЫЙ"
                c2.warning(f"**{side} вал выше на {abs(diff):.3f} мм** \n({abs(diff/screw_pitch):.2f} об.)")
            else:
                # Tri-Z: 2 спереди по углам, 1 сзади по центру
                f_left = matrix[0, 0]
                f_right = matrix[0, -1]
                b_center = matrix[-1, grid_x // 2]
                
                low = min(f_left, f_right, b_center)
                z1, z2, z3 = st.columns(3)
                points = [("Спереди Слева", f_left, z1), ("Спереди Справа", f_right, z2), ("Сзади Центр", b_center, z3)]
                
                for name, val, col in points:
                    d = val - low
                    with col:
                        st.info(f"**{name}**")
                        if d == 0: st.success("Опорная точка")
                        else: st.warning(f"{'🔽 Вниз' if d>0 else '🔼 Вверх'}  \n**{abs(d/screw_pitch):.2f}** об.")

            # --- ВИНТЫ (УГЛЫ) ---
            st.divider()
            st.subheader("🛠️ Регулировка угловых винтов")
            corners = {"ПЛ": matrix[0,0], "ПП": matrix[0,-1], "ЗЛ": matrix[-1,0], "ЗП": matrix[-1,-1]}
            low_c = min(corners.values())
            cols = st.columns(4)
            for (k, v), col in zip(corners.items(), cols):
                d = v - low_c
                with col:
                    st.info(f"**{k}**")
                    if d == 0: st.success("OK")
                    else: st.warning(f"**{abs(d/screw_pitch):.2f}** об.")