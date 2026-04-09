import streamlit as st
import plotly.graph_objects as go
import matplotlib.pyplot as plt
import matplotlib.patheffects as path_effects
import numpy as np
import re
import json

# Настройка страницы
st.set_page_config(page_title="Bed Mesh Visualizer Pro v5.1", layout="wide")

st.title("📏 Bed Mesh Visualizer Pro v5.1")

# Инициализация состояния сессии, чтобы графики не пропадали
if 'matrix' not in st.session_state:
    st.session_state.matrix = None

# --- БОКОВАЯ ПАНЕЛЬ ---
st.sidebar.header("📂 Данные")
uploaded_file = st.sidebar.file_uploader("Загрузить конфигурацию", type=['cfg', 'txt', 'json'])

default_vals = {"grid_x": 5, "grid_y": 5, "min_x": 10.0, "max_x": 240.0, "min_y": 10.0, "max_y": 240.0, "points": ""}

if uploaded_file:
    content = uploaded_file.read().decode("utf-8")
    try:
        if content.strip().startswith('{'):
            js = json.loads(content).get("bed_mesh default", {})
            if js:
                default_vals.update({
                    "grid_x": int(js.get("x_count", 5)), "grid_y": int(js.get("y_count", 5)),
                    "min_x": float(js.get("min_x", 5)), "max_x": float(js.get("max_x", 245)),
                    "min_y": float(js.get("min_y", 5)), "max_y": float(js.get("max_y", 245)),
                    "points": js.get("points", "").strip()
                })
        else:
            def fnd(p, t, d): return re.search(p, t).group(1) if re.search(p, t) else d
            default_vals.update({
                "grid_x": int(fnd(r"x_count\s*=\s*(\d+)", content, 5)),
                "grid_y": int(fnd(r"y_count\s*=\s*(\d+)", content, 5))
            })
            pts = re.search(r"points\s*=\s*([\s\S]+?)(?=\n\s*[a-zA-Z_]+\s*=|\[|\Z)", content)
            if pts: default_vals["points"] = pts.group(1).strip()
    except: st.sidebar.error("Ошибка парсинга.")

st.sidebar.header("⚙️ Геометрия стола")
bed_x = st.sidebar.number_input("Размер X (мм)", value=250)
bed_y = st.sidebar.number_input("Размер Y (мм)", value=250)
grid_x = st.sidebar.number_input("Точек X", value=default_vals["grid_x"])
grid_y = st.sidebar.number_input("Точек Y", value=default_vals["grid_y"])

# --- ВВОД ДАННЫХ ---
data_input = st.text_area("Данные точек (Mesh Points):", value=default_vals["points"], height=150)

if st.button("🚀 ВИЗУАЛИЗИРОВАТЬ", use_container_width=True):
    if data_input:
        nums = [float(n) for n in re.findall(r"[-+]?\d*\.\d+|\d+", data_input)]
        if len(nums) < grid_x * grid_y:
            st.error("Недостаточно точек!")
        else:
            # Расчет матрицы
            matrix = np.array(nums[:grid_x*grid_y]).reshape((grid_y, grid_x))
            # Логика змейки
            for i in range(len(matrix)):
                if i % 2 != 0: matrix[i] = matrix[i][::-1]
            # Сохраняем в сессию
            st.session_state.matrix = matrix
    else:
        st.info("Вставьте данные точек.")

# --- ОТОБРАЖЕНИЕ РЕЗУЛЬТАТОВ (если матрица есть в памяти) ---
if st.session_state.matrix is not None:
    matrix = st.session_state.matrix
    
    # Метрики
    v = np.max(matrix) - np.min(matrix)
    m1, m2, m3 = st.columns(3)
    m1.metric("Variance (Отклонение)", f"{v:.3f} мм")
    m2.metric("Max Z", f"{np.max(matrix):.3f} мм")
    m3.metric("Min Z", f"{np.min(matrix):.3f} мм")

    tab1, tab2 = st.tabs(["📊 3D Модель", "🗺️ 2D Карта"])
    
    with tab1:
        fig3 = go.Figure(data=[go.Surface(z=matrix, colorscale='RdYlBu_r')])
        fig3.update_layout(scene=dict(xaxis=dict(range=[0, grid_x-1]), yaxis=dict(range=[0, grid_y-1])), width=800, height=800)
        st.plotly_chart(fig3, use_container_width=True)

    with tab2:
        fig2, ax = plt.subplots(figsize=(8, 8))
        xe = np.linspace(0, bed_x, grid_x + 1); ye = np.linspace(0, bed_y, grid_y + 1)
        im = ax.pcolormesh(xe, ye, matrix, cmap='RdYlBu_r', edgecolors='black', linewidth=1)
        xc, yc = (xe[:-1] + xe[1:]) / 2, (ye[:-1] + ye[1:]) / 2
        for i in range(grid_y):
            for j in range(grid_x):
                t = ax.text(xc[j], yc[i], f"{matrix[i,j]:.3f}", ha="center", va="center", fontweight='bold')
                t.set_path_effects([path_effects.withStroke(linewidth=2, foreground="white")])
        ax.set_aspect('equal'); fig2.colorbar(im); st.pyplot(fig2)

    # --- РЕКОМЕНДАЦИИ ПО ВЫРАВНИВАНИЮ ---
    st.divider()
    st.header("🛠️ Рекомендации по выравниванию")
    
    r_col1, r_col2 = st.columns([1, 2])
    with r_col1:
        st.write("##### Настройки системы")
        z_sys = st.selectbox("Тип Z-привода:", 
                            ["Винты (только углы)", "2 вала (Л/П)", "3 вала (Tri-Z)", "4 вала (Quad-Z)"],
                            key="z_sys_select")
        pitch = st.selectbox("Шаг резьбы (мм):", [0.7, 0.5, 0.8, 1.0, 2.0], index=0, key="pitch_select")

    with r_col2:
        st.write("##### Инструкция по настройке")
        
        points = {}
        if z_sys == "Винты (только углы)":
            points = {"ПЛ (0,0)": matrix[0,0], "ПП (X,0)": matrix[0,-1], "ЗЛ (0,Y)": matrix[-1,0], "ЗП (X,Y)": matrix[-1,-1]}
        elif z_sys == "2 вала (Л/П)":
            points = {"Левый вал (среднее)": np.mean(matrix[:, 0]), "Правый вал (среднее)": np.mean(matrix[:, -1])}
        elif z_sys == "3 вала (Tri-Z)":
            points = {"Передний Левый": matrix[0,0], "Передний Правый": matrix[0,-1], "Задний Центр": matrix[-1, grid_x//2]}
        elif z_sys == "4 вала (Quad-Z)":
            points = {"Передний Левый": matrix[0,0], "Передний Правый": matrix[0,-1], "Задний Левый": matrix[-1,0], "Задний Правый": matrix[-1,-1]}

        low = min(points.values())
        res_cols = st.columns(len(points))
        for (name, val), col in zip(points.items(), res_cols):
            diff = val - low
            with col:
                if diff == 0:
                    st.success(f"**{name}** \nОПОРА")
                else:
                    st.warning(f"**{name}** \n{diff:+.3f} мм  \n**{abs(diff/pitch):.2f} об.** \n{'🔽 ВНИЗ' if diff>0 else '🔼 ВВЕРХ'}")