import streamlit as st
import plotly.graph_objects as go
import matplotlib.pyplot as plt
import matplotlib.patheffects as path_effects
import numpy as np
import re
import json

# Настройка страницы
st.set_page_config(page_title="Bed Mesh Visualizer Pro v5.5.0", layout="wide")

# --- CSS ---
st.markdown("""
    <style>
    .block-container { padding-top: 1.5rem; }
    [data-testid="stMetricValue"] { font-size: 1.1rem !important; color: #00ffcc; }
    [data-testid="stMetricLabel"] { font-size: 0.75rem !important; }
    .stAlert { padding: 8px !important; margin-bottom: 4px !important; }
    hr { margin: 1rem 0 !important; }
    </style>
    """, unsafe_allow_html=True)

st.title("📏 Bed Mesh Visualizer Pro v5.5.0")

if 'matrix' not in st.session_state:
    st.session_state.matrix = None

# --- SIDEBAR ---
with st.sidebar:
    st.header("📂 Данные")
    uploaded_file = st.file_uploader("Загрузить конфиг", type=['cfg', 'txt', 'json'])
    default_vals = {"grid_x": 5, "grid_y": 5, "points": ""}
    
    if uploaded_file:
        content = uploaded_file.read().decode("utf-8")
        try:
            if content.strip().startswith('{'):
                js = json.loads(content).get("bed_mesh default", {})
                if js: default_vals.update({"grid_x": int(js.get("x_count", 5)), "grid_y": int(js.get("y_count", 5)), "points": js.get("points", "").strip()})
            else:
                def fnd(p, t, d): return re.search(p, t).group(1) if re.search(p, t) else d
                default_vals.update({"grid_x": int(fnd(r"x_count\s*=\s*(\d+)", content, 5)), "grid_y": int(fnd(r"y_count\s*=\s*(\d+)", content, 5))})
                pts = re.search(r"points\s*=\s*([\s\S]+?)(?=\n\s*[a-zA-Z_]+\s*=|\[|\Z)", content)
                if pts: default_vals["points"] = pts.group(1).strip()
        except: st.error("Ошибка парсинга.")

    bed_x = st.number_input("Размер X", value=250)
    bed_y = st.number_input("Размер Y", value=250)
    grid_x = st.number_input("Точек X", value=default_vals["grid_x"])
    grid_y = st.number_input("Точек Y", value=default_vals["grid_y"])

data_input = st.text_area("Mesh Points:", value=default_vals["points"], height=100)

if st.button("🚀 ВИЗУАЛИЗИРОВАТЬ", use_container_width=True):
    if data_input:
        # Извлекаем все числа
        nums = [float(n) for n in re.findall(r"[-+]?\d*\.\d+|\d+", data_input)]
        
        if len(nums) < grid_x * grid_y:
            st.error(f"Нужно {grid_x * grid_y} точек. Найдено: {len(nums)}")
        else:
            # НОВАЯ ЛОГИКА: Просто решейпим массив. 
            # Точки идут слева направо ряд за рядом.
            matrix = np.array(nums[:grid_x*grid_y]).reshape((grid_y, grid_x))
            
            # УДАЛЕНО: блок с разворотом нечетных строк matrix[i][::-1]
            
            st.session_state.matrix = matrix

st.divider()

# --- MAIN ---
if st.session_state.matrix is not None:
    matrix = st.session_state.matrix
    col_viz, col_rec = st.columns([1.6, 1], gap="medium")

    with col_viz:
        tab1, tab2 = st.tabs(["📊 3D Рельеф", "🗺️ 2D Карта"])
        
        with tab1:
            x_c, y_c = np.linspace(0, bed_x, grid_x), np.linspace(0, bed_y, grid_y)
            fig3 = go.Figure(data=[go.Surface(z=matrix, x=x_c, y=y_c, colorscale='RdYlBu_r')])
            fig3.update_layout(
                scene=dict(xaxis_title='X', yaxis_title='Y', zaxis_title='Z'),
                margin=dict(l=0, r=0, b=0, t=0), 
                height=500
            )
            st.plotly_chart(fig3, use_container_width=True)

        with tab2:
            # Уплотненная колонка для уменьшения 2D карты
            sub_col1, _ = st.columns([1, 1]) 
            with sub_col1:
                fig2, ax = plt.subplots(figsize=(4, 4), dpi=100) 
                fig2.patch.set_facecolor('#0e1117')
                
                xe, ye = np.linspace(0, bed_x, grid_x + 1), np.linspace(0, bed_y, grid_y + 1)
                im = ax.pcolormesh(xe, ye, matrix, cmap='RdYlBu_r', edgecolors='#1e1e1e', linewidth=0.5)
                
                xc, yc = (xe[:-1] + xe[1:]) / 2, (ye[:-1] + ye[1:]) / 2
                for i in range(grid_y):
                    for j in range(grid_x):
                        t = ax.text(xc[j], yc[i], f"{matrix[i,j]:.2f}", ha="center", va="center", 
                                    color="white", fontsize=7, fontweight='bold')
                        t.set_path_effects([path_effects.withStroke(linewidth=1.2, foreground="black")])
                
                ax.set_aspect('equal')
                ax.tick_params(colors='gray', labelsize=7)
                plt.tight_layout(pad=0.2)
                st.pyplot(fig2)

    with col_rec:
        st.write("### 📝 Анализ")
        r1_1, r1_2, r1_3 = st.columns(3)
        r1_1.metric("Мин", f"{np.min(matrix):.3f}")
        r1_2.metric("Макс", f"{np.max(matrix):.3f}")
        r1_3.metric("Размах", f"{(np.max(matrix) - np.min(matrix)):.3f}")
        
        r2_1, r2_2, r2_3 = st.columns(3)
        r2_1.metric("Среднее", f"{np.mean(matrix):.3f}")
        r2_2.metric("Вариация", f"{np.var(matrix):.3f}")
        r2_3.metric("RMS", f"{np.sqrt(np.mean(matrix**2)):.3f}")
        
        st.divider()
        st.write("### 🛠️ Настройка")
        z_sys = st.selectbox("Привод", ["Винты (углы)", "2 вала (Л/П)", "3 вала (Tri-Z)", "4 вала (Quad-Z)"])
        is_shafts = "вала" in z_sys.lower()
        
        p_val = 0.7
        if not is_shafts:
            p_val = st.selectbox("Шаг", [0.7, 0.5, 0.4, 0.8, 1.0, 2.0])

        points = {}
        if "Винты" in z_sys or "4 вала" in z_sys:
            points = {"ПЛ": matrix[0,0], "ПП": matrix[0,-1], "ЗЛ": matrix[-1,0], "ЗП": matrix[-1,-1]}
        elif "2 вала" in z_sys:
            points = {"Левый": np.mean(matrix[:, 0]), "Правый": np.mean(matrix[:, -1])}
        elif "3 вала" in z_sys:
            points = {"ПЛ": matrix[0,0], "ПП": matrix[0,-1], "З-Центр": matrix[-1, grid_x//2]}

        low = min(points.values())
        for name, val in points.items():
            diff = val - low
            if diff < 0.005: st.success(f"**{name}**: ОПОРА")
            else:
                direction = "🔽" if diff > 0 else "🔼"
                if is_shafts: st.info(f"**{name}**: {abs(diff):.3f} мм {direction}")
                else: st.warning(f"**{name}**: {abs(diff/p_val):.2f} об. {direction}")