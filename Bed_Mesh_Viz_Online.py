import streamlit as st
import plotly.graph_objects as go
import matplotlib.pyplot as plt
import matplotlib.patheffects as path_effects
import numpy as np
import re
import json
import streamlit.components.v1 as components

# Настройка страницы
st.set_page_config(page_title="Bed Mesh Visualizer", layout="wide")

# --- ФУНКЦИЯ АНАЛИТИКИ (GA4) ---
# Если у тебя есть Google Analytics, вставь свой ID (G-XXXXXXXXXX)
def inject_ga(ga_id="G-XXXXXXXXXX"):
    if ga_id != "G-XXXXXXXXXX":
        ga_js = f"""
        <script async src="https://www.googletagmanager.com/gtag/js?id={ga_id}"></script>
        <script>
            window.dataLayer = window.dataLayer || [];
            function gtag(){{dataLayer.push(arguments);}}
            gtag('js', new Date());
            gtag('config', '{ga_id}');
        </script>
        """
        components.html(ga_js, height=0)

# Вызываем аналитику (по умолчанию ничего не делает, пока не сменишь ID)
inject_ga()

# Название и версия
st.title("📏 Bed Mesh Visualizer v4.8")

# Инициализация состояния сессии
if 'analyzed' not in st.session_state:
    st.session_state.analyzed = False
if 'matrix' not in st.session_state:
    st.session_state.matrix = None
if 'last_file_id' not in st.session_state:
    st.session_state.last_file_id = None

# --- БОКОВАЯ ПАНЕЛЬ ---
st.sidebar.header("📂 Загрузка конфигурации")
uploaded_file = st.sidebar.file_uploader("Загрузить printer_mutable.cfg", type=['cfg', 'txt', 'conf'])

# Логика сброса при удалении файла
if uploaded_file is None and st.session_state.last_file_id is not None:
    st.session_state.analyzed = False
    st.session_state.matrix = None
    st.session_state.last_file_id = None
    st.rerun()

# Настройки по умолчанию (на основе твоего конфига)
default_vals = {
    "grid_x": 10, "grid_y": 10,
    "min_x": 5.0, "max_x": 244.94,
    "min_y": 5.0, "max_y": 244.94,
    "points": ""
}

if uploaded_file is not None:
    st.session_state.last_file_id = uploaded_file.name
    try:
        raw_content = uploaded_file.read().decode("utf-8")
        # Парсинг JSON ( printer_mutable.cfg )
        if raw_content.strip().startswith('{'):
            data = json.loads(raw_content)
            mesh_data = data.get("bed_mesh default", {})
            if mesh_data:
                default_vals["grid_x"] = int(mesh_data.get("x_count", 10))
                default_vals["grid_y"] = int(mesh_data.get("y_count", 10))
                default_vals["min_x"] = float(mesh_data.get("min_x", 5))
                default_vals["max_x"] = float(mesh_data.get("max_x", 244.94))
                default_vals["min_y"] = float(mesh_data.get("min_y", 5))
                default_vals["max_y"] = float(mesh_data.get("max_y", 244.94))
                default_vals["points"] = mesh_data.get("points", "").strip()
                st.sidebar.success("✅ Данные загружены")
        # Парсинг обычного текстового CFG
        else:
            def get_val(pattern, text, default):
                match = re.search(pattern, text)
                return match.group(1) if match else default
            default_vals["grid_x"] = int(get_val(r"x_count\s*=\s*(\d+)", raw_content, 10))
            default_vals["grid_y"] = int(get_val(r"y_count\s*=\s*(\d+)", raw_content, 10))
            default_vals["min_x"] = float(get_val(r"min_x\s*=\s*([\d.]+)", raw_content, 5))
            default_vals["max_x"] = float(get_val(r"max_x\s*=\s*([\d.]+)", raw_content, 244.94))
            default_vals["min_y"] = float(get_val(r"min_y\s*=\s*([\d.]+)", raw_content, 5))
            default_vals["max_y"] = float(get_val(r"max_y\s*=\s*([\d.]+)", raw_content, 244.94))
            p_match = re.search(r"points\s*=\s*([\s\S]+?)(?=\n\s*[a-zA-Z_]+\s*=|\[|\Z)", raw_content)
            if p_match: default_vals["points"] = p_match.group(1).strip()
    except Exception as e:
        st.sidebar.error(f"Ошибка файла: {str(e)}")

st.sidebar.header("1. Параметры стола")
bed_x = st.sidebar.number_input("Размер стола X", value=250)
bed_y = st.sidebar.number_input("Размер стола Y", value=250)

st.sidebar.header("2. Настройки сетки")
gx = st.sidebar.number_input("Точек по X", value=default_vals["grid_x"])
gy = st.sidebar.number_input("Точек по Y", value=default_vals["grid_y"])
mx_min = st.sidebar.number_input("Min X", value=default_vals["min_x"])
mx_max = st.sidebar.number_input("Max X", value=default_vals["max_x"])
my_min = st.sidebar.number_input("Min Y", value=default_vals["min_y"])
my_max = st.sidebar.number_input("Max Y", value=default_vals["max_y"])

origin = st.sidebar.selectbox("Начало координат (0,0)", ["Левый-ближний угол", "Левый-дальний угол", "Правый-ближний угол", "Правый-дальний угол"])

# --- ОСНОВНАЯ ЧАСТЬ ---
data_input = st.text_area("Данные точек:", value=default_vals["points"], height=100)

if st.button("ПОСТРОИТЬ И АНАЛИЗИРОВАТЬ"):
    if data_input:
        raw_nums = re.findall(r"[-+]?\d*\.\d+|\d+", data_input)
        nums = [float(n) for n in raw_nums]
        if len(nums) >= (gx * gy):
            st.session_state.matrix = np.array(nums[-(gx*gy):]).reshape((gy, gx))
            st.session_state.analyzed = True
        else:
            st.error(f"Недостаточно данных: {len(nums)} из {gx*gy}.")

# --- ВИЗУАЛИЗАЦИЯ ---
if st.session_state.analyzed:
    display_matrix = st.session_state.matrix.copy()
    if origin == "Левый-дальний угол": display_matrix = np.flipud(display_matrix)
    elif origin == "Правый-ближний угол": display_matrix = np.fliplr(display_matrix)
    elif origin == "Правый-дальний угол": display_matrix = np.flipud(np.fliplr(display_matrix))

    col_left, col_right = st.columns(2)

    with col_left:
        st.markdown("### 📊 3D Интерактив")
        fig3 = go.Figure(data=[go.Surface(x=np.linspace(mx_min, mx_max, gx), y=np.linspace(my_min, my_max, gy), z=display_matrix, colorscale='RdYlBu_r')])
        fig3.update_layout(scene=dict(xaxis_range=[0, bed_x], yaxis_range=[0, bed_y], aspectratio=dict(x=1, y=1, z=0.4)), margin=dict(l=0, r=0, b=0, t=0), height=600)
        st.plotly_chart(fig3, use_container_width=True)

    with col_right:
        st.markdown("### 🗺️ 2D Карта")
        xe, ye = np.linspace(0, bed_x, gx+1), np.linspace(0, bed_y, gy+1)
        xc, yc = (xe[:-1]+xe[1:])/2, (ye[:-1]+ye[1:])/2
        fig2, ax = plt.subplots(figsize=(8, 8))
        im = ax.pcolormesh(xe, ye, display_matrix, cmap='RdYlBu_r', edgecolors='black', linewidth=0.5)
        f_size = 7 if gx > 7 else 9
        for i in range(gy):
            for j in range(gx):
                txt = ax.text(xc[j], yc[i], f"{display_matrix[i,j]:.3f}", ha="center", va="center", fontweight='bold', fontsize=f_size)
                txt.set_path_effects([path_effects.withStroke(linewidth=1.5, foreground="white")])
        ax.set_aspect('equal')
        ax.set_xticks(xe); ax.set_yticks(ye)
        ax.tick_params(labelsize=7)
        st.pyplot(fig2)

    st.divider()
    with st.expander("🔧 Мастер выравнивания", expanded=True):
        method = st.radio("Метод:", ["Винты", "Валы Z"], horizontal=True)
        if method == "Винты":
            p = st.selectbox("Шаг винтов", [0.7, 0.5, 0.8], format_func=lambda x: f"M4 (0.7мм)" if x==0.7 else f"M3 (0.5мм)")
            crn = {"П-Л": display_matrix[0,0], "П-П": display_matrix[0,-1], "З-Л": display_matrix[-1,0], "З-П": display_matrix[-1,-1]}
            target = min(crn.values())
            cols = st.columns(4)
            for i, (name, val) in enumerate(crn.items()):
                diff = val - target
                with cols[i]:
                    st.metric(name, f"{val:.2f}", f"{diff:+.3f} мм")
                    if abs(diff) > 0.01: st.write(f"**{abs(diff)/p:.2f}** об. ({'ВНИЗ' if diff > 0 else 'ВВЕРХ'})")
        else:
            z_mode = st.selectbox("Валов Z:", [2, 3, 4])
            pts = {}
            if z_mode == 2: pts = {"Левый": np.mean(display_matrix[:,0]), "Правый": np.mean(display_matrix[:,-1])}
            elif z_mode == 3:
                layout = st.selectbox("Схема:", ["2 Спереди + 1 Сзади (центр)", "1 Спереди (центр) + 2 Сзади", "Лево + Право + Сзади (центр)"])
                if "2 Спереди" in layout: pts = {"Перед-Л": display_matrix[0,0], "Перед-П": display_matrix[0,-1], "Зад-Ц": display_matrix[-1, gx//2]}
                elif "1 Спереди" in layout: pts = {"Перед-Ц": display_matrix[0, gx//2], "Зад-Л": display_matrix[-1,0], "Зад-П": display_matrix[-1,-1]}
                else: pts = {"Лево-Ц": display_matrix[gy//2, 0], "Право-Ц": display_matrix[gy//2, -1], "Зад-Ц": display_matrix[-1, gx//2]}
            else: pts = {"П-Л": display_matrix[0,0], "П-П": display_matrix[0,-1], "З-Л": display_matrix[-1,0], "З-П": display_matrix[-1,-1]}
            avg = np.mean(list(pts.values()))
            cols = st.columns(len(pts))
            for i, (name, val) in enumerate(pts.items()):
                diff = val - avg
                with cols[i]:
                    st.metric(name, f"{val:.2f}", f"{diff:+.3f} мм")
                    st.write(f"**{abs(diff):.3f} мм** ({'ВНИЗ' if diff > 0 else 'ВВЕРХ'})")
else:
    st.info("Загрузите конфигурацию или введите данные.")