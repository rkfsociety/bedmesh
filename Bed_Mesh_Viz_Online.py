import streamlit as st
import plotly.graph_objects as go
import matplotlib.pyplot as plt
import matplotlib.patheffects as path_effects
import numpy as np
import re
import json

# Настройка страницы
st.set_page_config(page_title="Bed Mesh Visualizer", layout="wide")

# Название зафиксировано, меняется только версия
st.title("📏 Bed Mesh Visualizer v4.2")

# Инициализация хранилища данных (чтобы данные не пропадали при переключении кнопок)
if 'analyzed' not in st.session_state:
    st.session_state.analyzed = False
if 'matrix' not in st.session_state:
    st.session_state.matrix = None

# --- БОКОВАЯ ПАНЕЛЬ ---
st.sidebar.header("📂 Загрузка конфигурации")
uploaded_file = st.sidebar.file_uploader("Загрузить printer_mutable.cfg", type=['cfg', 'txt', 'conf'])

# Настройки по умолчанию
default_vals = {
    "grid_x": 5, "grid_y": 5,
    "min_x": 10.0, "max_x": 240.0,
    "min_y": 10.0, "max_y": 240.0,
    "points": ""
}

# Парсинг файла
if uploaded_file is not None:
    try:
        raw_content = uploaded_file.read().decode("utf-8")
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
                st.sidebar.success("✅ Данные загружены")
        else:
            def get_val(pattern, text, default):
                match = re.search(pattern, text)
                return match.group(1) if match else default
            default_vals["grid_x"] = int(get_val(r"x_count\s*=\s*(\d+)", raw_content, 5))
            default_vals["grid_y"] = int(get_val(r"y_count\s*=\s*(\d+)", raw_content, 5))
            default_vals["min_x"] = float(get_val(r"min_x\s*=\s*([\d.]+)", raw_content, 5))
            default_vals["max_x"] = float(get_val(r"max_x\s*=\s*([\d.]+)", raw_content, 245))
            default_vals["min_y"] = float(get_val(r"min_y\s*=\s*([\d.]+)", raw_content, 5))
            default_vals["max_y"] = float(get_val(r"max_y\s*=\s*([\d.]+)", raw_content, 245))
            p_match = re.search(r"points\s*=\s*([\s\S]+?)(?=\n\s*[a-zA-Z_]+\s*=|\[|\Z)", raw_content)
            if p_match: default_vals["points"] = p_match.group(1).strip()
    except Exception as e:
        st.sidebar.error(f"Ошибка чтения: {str(e)}")

st.sidebar.header("1. Физические параметры")
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

# --- ВВОД ДАННЫХ ---
data_input = st.text_area("Данные точек:", value=default_vals["points"], height=150)

if st.button("ПОСТРОИТЬ И АНАЛИЗИРОВАТЬ"):
    if data_input:
        raw_nums = re.findall(r"[-+]?\d*\.\d+|\d+", data_input)
        nums = [float(n) for n in raw_nums]
        if len(nums) >= (gx * gy):
            # Сохраняем результат в состояние сессии
            st.session_state.matrix = np.array(nums[-(gx*gy):]).reshape((gy, gx))
            st.session_state.analyzed = True
        else:
            st.error(f"Недостаточно данных: найдено {len(nums)} из {gx*gy}.")

# --- ОТОБРАЖЕНИЕ РЕЗУЛЬТАТОВ ---
if st.session_state.analyzed:
    # Подготовка матрицы с учетом ориентации
    display_matrix = st.session_state.matrix.copy()
    if origin == "Левый-дальний угол": display_matrix = np.flipud(display_matrix)
    elif origin == "Правый-ближний угол": display_matrix = np.fliplr(display_matrix)
    elif origin == "Правый-дальний угол": display_matrix = np.flipud(np.fliplr(display_matrix))

    tab1, tab2, tab3 = st.tabs(["📊 3D Интерактив", "🗺️ 2D Карта", "🔧 Мастер выравнивания"])

    with tab1:
        fig3 = go.Figure(data=[go.Surface(x=np.linspace(mx_min, mx_max, gx), y=np.linspace(my_min, my_max, gy), z=display_matrix, colorscale='RdYlBu_r')])
        fig3.update_layout(scene=dict(xaxis_range=[0, bed_x], yaxis_range=[0, bed_y], aspectratio=dict(x=1, y=1, z=0.4)))
        st.plotly_chart(fig3, use_container_width=True)

    with tab2:
        xe, ye = np.linspace(0, bed_x, gx+1), np.linspace(0, bed_y, gy+1)
        xc, yc = (xe[:-1]+xe[1:])/2, (ye[:-1]+ye[1:])/2
        fig2, ax = plt.subplots(figsize=(8, 8))
        im = ax.pcolormesh(xe, ye, display_matrix, cmap='RdYlBu_r', edgecolors='black')
        for i in range(gy):
            for j in range(gx):
                txt = ax.text(xc[j], yc[i], f"{display_matrix[i,j]:.3f}", ha="center", va="center", fontweight='bold')
                txt.set_path_effects([path_effects.withStroke(linewidth=2, foreground="white")])
        ax.set_aspect('equal')
        st.pyplot(fig2)

    with tab3:
        # Теперь переключение этих кнопок не сбрасывает графики выше
        method = st.radio("Метод регулировки:", ["Винты (пружины)", "Валы (моторы Z)"], key="corr_method")
        
        if method == "Винты (пружины)":
            pitch = st.selectbox("Шаг резьбы", [0.7, 0.5, 0.8], format_func=lambda x: f"M4 (0.7мм)" if x==0.7 else f"M3 (0.5мм)")
            crn = {"П-Л": display_matrix[0,0], "П-П": display_matrix[0,-1], "З-Л": display_matrix[-1,0], "З-П": display_matrix[-1,-1]}
            base = min(crn.values())
            cols = st.columns(2)
            for i, (name, val) in enumerate(crn.items()):
                diff = val - base
                with cols[i%2]:
                    st.metric(name, f"{val:.3f} мм", f"{diff:+.3f} мм")
                    if abs(diff) > 0.01: 
                        st.write(f"🔧 Крутить: **{abs(diff)/pitch:.2f}** об. ({'ВНИЗ' if diff > 0 else 'ВВЕРХ'})")
        
        else:
            z_mode = st.selectbox("Конфигурация Z:", [2, 3, 4], key="z_count")
            if z_mode == 2:
                pts = {"Левый вал": np.mean(display_matrix[:,0]), "Правый вал": np.mean(display_matrix[:,-1])}
            elif z_mode == 3:
                pts = {"Перед (центр)": display_matrix[0, gx//2], "Зад-Лево": display_matrix[-1,0], "Зад-Право": display_matrix[-1,-1]}
            else:
                pts = {"П-Л": display_matrix[0,0], "П-П": display_matrix[0,-1], "З-Л": display_matrix[-1,0], "З-П": display_matrix[-1,-1]}
            
            avg = np.mean(list(pts.values()))
            cols = st.columns(2)
            for i, (name, val) in enumerate(pts.items()):
                diff = val - avg
                with cols[i%2]:
                    st.metric(name, f"{val:.3f} мм", f"{diff:+.3f} мм")
                    st.write(f"⚙️ Сдвиг: **{abs(diff):.3f} мм** ({'ВНИЗ' if diff > 0 else 'ВВЕРХ'})")
else:
    st.info("Загрузите файл или вставьте данные, затем нажмите кнопку анализа.")