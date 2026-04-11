import streamlit as st
import plotly.graph_objects as go
import matplotlib.pyplot as plt
import matplotlib.patheffects as path_effects
import numpy as np
import re
import json

# Настройка страницы
st.set_page_config(page_title="Bed Mesh Visualizer Pro v5.4.6", layout="wide")

# --- CSS ДЛЯ УЛЬТРА-КОМПАКТНОСТИ ---
st.markdown("""
    <style>
    /* Уплотняем всё приложение */
    .block-container { padding-top: 1rem; padding-bottom: 0rem; }
    
    /* Ограничиваем графики */
    .stPlotlyChart, [data-testid="stPyplotChart"] {
        max-width: 450px !important;
        margin: 0 auto;
    }
    
    /* Уменьшаем шрифт и отступы в метриках анализа */
    [data-testid="stMetricValue"] { font-size: 1.2rem !important; }
    [data-testid="stMetricLabel"] { font-size: 0.8rem !important; }
    div[data-testid="column"] { padding: 0px !important; }

    /* Компактные карточки рекомендаций */
    .stAlert { padding: 5px 10px !important; margin-bottom: 5px !important; }
    p, round { margin-bottom: 2px !important; }
    
    /* Уменьшаем высоту текстового поля и селекторов */
    .stTextArea textarea { height: 80px !important; }
    .stSelectbox div[data-baseweb="select"] { min-height: 30px !important; }
    
    /* Скрываем лишние отступы у заголовков */
    h1 { padding: 0; margin-bottom: 0.5rem; font-size: 1.5rem !important; }
    h2, h3 { margin-top: 0.5rem !important; margin-bottom: 0.5rem !important; font-size: 1.1rem !important; }
    
    hr { margin: 0.5rem 0 !important; }
    </style>
    """, unsafe_allow_html=True)

st.title("📏 Bed Mesh Visualizer Pro v5.4.6")

# Инициализация состояния сессии
if 'matrix' not in st.session_state:
    st.session_state.matrix = None

# --- БОКОВАЯ ПАНЕЛЬ ---
st.sidebar.header("📂 Данные")
uploaded_file = st.sidebar.file_uploader("Загрузить конфигурацию", type=['cfg', 'txt', 'json'])

default_vals = {"grid_x": 5, "grid_y": 5, "points": ""}

if uploaded_file:
    content = uploaded_file.read().decode("utf-8")
    try:
        if content.strip().startswith('{'):
            js = json.loads(content).get("bed_mesh default", {})
            if js:
                default_vals.update({
                    "grid_x": int(js.get("x_count", 5)), "grid_y": int(js.get("y_count", 5)),
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

st.sidebar.header("⚙️ Геометрия")
bed_x = st.sidebar.number_input("Размер X", value=250)
bed_y = st.sidebar.number_input("Размер Y", value=250)
grid_x = st.sidebar.number_input("Точек X", value=default_vals["grid_x"])
grid_y = st.sidebar.number_input("Точек Y", value=default_vals["grid_y"])

# Ввод данных
data_input = st.text_area("Данные точек (Mesh Points):", value=default_vals["points"])

if st.button("🚀 ВИЗУАЛИЗИРОВАТЬ", use_container_width=True):
    if data_input:
        nums = [float(n) for n in re.findall(r"[-+]?\d*\.\d+|\d+", data_input)]
        if len(nums) < grid_x * grid_y:
            st.error(f"Нужно {grid_x * grid_y} точек.")
        else:
            matrix = np.array(nums[:grid_x*grid_y]).reshape((grid_y, grid_x))
            for i in range(len(matrix)):
                if i % 2 != 0: matrix[i] = matrix[i][::-1]
            st.session_state.matrix = matrix

st.divider()

# --- ОСНОВНОЙ КОНТЕНТ ---
if st.session_state.matrix is not None:
    matrix = st.session_state.matrix
    
    col_viz, col_rec = st.columns([1.8, 1], gap="small")

    with col_viz:
        tab1, tab2 = st.tabs(["📊 3D", "🗺️ 2D"])
        x_coords = np.linspace(0, bed_x, grid_x)
        y_coords = np.linspace(0, bed_y, grid_y)

        with tab1:
            fig3 = go.Figure(data=[go.Surface(z=matrix, x=x_coords, y=y_coords, colorscale='RdYlBu_r')])
            fig3.update_layout(
                scene=dict(xaxis_title='X', yaxis_title='Y', zaxis_title='Z'),
                margin=dict(l=0, r=0, b=0, t=0),
                width=450, height=450, autosize=False
            )
            st.plotly_chart(fig3, use_container_width=False)

        with tab2:
            fig2, ax = plt.subplots(figsize=(4.5, 4.5), dpi=100) 
            fig2.patch.set_facecolor('#f0f2f6')
            xe = np.linspace(0, bed_x, grid_x + 1)
            ye = np.linspace(0, bed_y, grid_y + 1)
            im = ax.pcolormesh(xe, ye, matrix, cmap='RdYlBu_r', edgecolors='black', linewidth=0.5)
            xc, yc = (xe[:-1] + xe[1:]) / 2, (ye[:-1] + ye[1:]) / 2
            for i in range(grid_y):
                for j in range(grid_x):
                    t = ax.text(xc[j], yc[i], f"{matrix[i,j]:.2f}", ha="center", va="center", fontweight='bold', fontsize=7)
                    t.set_path_effects([path_effects.withStroke(linewidth=1.2, foreground="white")])
            ax.set_aspect('equal')
            plt.tight_layout(pad=0)
            st.pyplot(fig2)

    with col_rec:
        st.write("### 📝 Анализ")
        m_col1, m_col2, m_col3 = st.columns(3)
        m_col1.metric("Мин", f"{np.min(matrix):.3f}")
        m_col2.metric("Макс", f"{np.max(matrix):.3f}")
        m_col3.metric("Размах", f"{np.max(matrix) - np.min(matrix):.3f}")
        
        m_col4, m_col5, m_col6 = st.columns(3)
        m_col4.metric("Среднее", f"{np.mean(matrix):.3f}")
        m_col5.metric("Вариация", f"{np.var(matrix):.3f}")
        m_col6.metric("RMS", f"{np.sqrt(np.mean(matrix**2)):.3f}")
        
        st.write("---")
        st.write("### 🛠️ Настройка")
        z_sys = st.selectbox("Привод:", 
                            ["Винты (углы)", "2 вала (Л/П)", "3 вала (Tri-Z)", "4 вала (Quad-Z)"], label_visibility="collapsed")
        is_shafts = "вала" in z_sys.lower()
        pitch = 1.0
        if not is_shafts:
            pitch = st.selectbox("Шаг:", [0.7, 0.5, 0.8, 1.0, 2.0], index=0, label_visibility="collapsed")
        
        # Точки
        points = {}
        if "Винты" in z_sys:
            points = {"ПЛ": matrix[0,0], "ПП": matrix[0,-1], "ЗЛ": matrix[-1,0], "ЗП": matrix[-1,-1]}
        elif "2 вала" in z_sys:
            points = {"Л-Вал": np.mean(matrix[:, 0]), "П-Вал": np.mean(matrix[:, -1])}
        elif "3 вала" in z_sys:
            points = {"ПЛ": matrix[0,0], "ПП": matrix[0,-1], "ЗЦ": matrix[-1, grid_x//2]}
        elif "4 вала" in z_sys:
            points = {"ПЛ": matrix[0,0], "ПП": matrix[0,-1], "ЗЛ": matrix[-1,0], "ЗП": matrix[-1,-1]}

        low = min(points.values())
        for name, val in points.items():
            diff = val - low
            if diff == 0:
                st.success(f"**{name}**: ОПОРА")
            else:
                direction = "🔽" if diff > 0 else "🔼"
                if is_shafts:
                    st.info(f"**{name}**: {abs(diff):.3f} мм {direction}")
                else:
                    st.warning(f"**{name}**: {abs(diff/pitch):.2f} об. ({diff:+.2f}) {direction}")