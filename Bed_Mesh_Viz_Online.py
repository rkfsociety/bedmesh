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

# --- K-коэффициенты шейпера (из shaper_calibrate.py Klipper, threshold=0.12, damping=0.1) ---
SHAPER_K = {
    "zv":       2.60,
    "mzv":      2.15,
    "zvd":      2.00,
    "ei":       1.60,
    "2hump_ei": 1.11,
    "3hump_ei": 0.85,
}
SHAPER_TYPES = list(SHAPER_K.keys())

# --- SIDEBAR ---
with st.sidebar:
    st.header("📂 Данные")
    uploaded_file = st.file_uploader("Загрузить конфиг", type=['cfg', 'txt', 'json'])
    default_vals = {
        "grid_x": 5, "grid_y": 5, "points": "",
        "shaper_type_x": "mzv", "shaper_freq_x": 0.0,
        "shaper_type_y": "mzv", "shaper_freq_y": 0.0,
    }

    if uploaded_file:
        content = uploaded_file.read().decode("utf-8")
        try:
            if content.strip().startswith('{'):
                js = json.loads(content).get("bed_mesh default", {})
                if js:
                    default_vals.update({
                        "grid_x": int(js.get("x_count", 5)),
                        "grid_y": int(js.get("y_count", 5)),
                        "points": js.get("points", "").strip(),
                    })
                # Шейпер из JSON (ключ "input_shaper")
                js_full = json.loads(content)
                sh = js_full.get("input_shaper", {})
                if sh:
                    tx = sh.get("shaper_type_x", sh.get("shaper_type", "mzv")).lower()
                    ty = sh.get("shaper_type_y", sh.get("shaper_type", "mzv")).lower()
                    fx = float(sh.get("shaper_freq_x", sh.get("shaper_freq", 0)) or 0)
                    fy = float(sh.get("shaper_freq_y", sh.get("shaper_freq", 0)) or 0)
                    if tx in SHAPER_K: default_vals["shaper_type_x"] = tx
                    if ty in SHAPER_K: default_vals["shaper_type_y"] = ty
                    if fx > 0: default_vals["shaper_freq_x"] = fx
                    if fy > 0: default_vals["shaper_freq_y"] = fy
            else:
                def fnd(p, t, d): return re.search(p, t).group(1) if re.search(p, t) else d
                default_vals.update({
                    "grid_x": int(fnd(r"x_count\s*=\s*(\d+)", content, 5)),
                    "grid_y": int(fnd(r"y_count\s*=\s*(\d+)", content, 5)),
                })
                pts = re.search(r"points\s*=\s*([\s\S]+?)(?=\n\s*[a-zA-Z_]+\s*=|\[|\Z)", content)
                if pts: default_vals["points"] = pts.group(1).strip()

                # Шейпер из текстового cfg
                sh_sec = re.search(r"\[input_shaper\]([\s\S]+?)(?=\n\s*\[|\Z)", content, re.IGNORECASE)
                if sh_sec:
                    sec = sh_sec.group(1)
                    def get_sh(key):
                        m = re.search(rf"^\s*{key}\s*[=:]\s*(.+)", sec, re.MULTILINE | re.IGNORECASE)
                        return m.group(1).strip().split("#")[0].strip() if m else None
                    tx = (get_sh("shaper_type_x") or get_sh("shaper_type") or "").lower()
                    ty = (get_sh("shaper_type_y") or get_sh("shaper_type") or "").lower()
                    fx = float(get_sh("shaper_freq_x") or get_sh("shaper_freq") or 0)
                    fy = float(get_sh("shaper_freq_y") or get_sh("shaper_freq") or 0)
                    if tx in SHAPER_K: default_vals["shaper_type_x"] = tx
                    if ty in SHAPER_K: default_vals["shaper_type_y"] = ty
                    if fx > 0: default_vals["shaper_freq_x"] = fx
                    if fy > 0: default_vals["shaper_freq_y"] = fy
        except:
            st.error("Ошибка парсинга.")

    bed_x = st.number_input("Размер X", value=250)
    bed_y = st.number_input("Размер Y", value=250)
    grid_x = st.number_input("Точек X", value=default_vals["grid_x"])
    grid_y = st.number_input("Точек Y", value=default_vals["grid_y"])

    st.divider()
    st.header("⚡ Шейпер")

    sh_type_x = st.selectbox(
        "Тип шейпера X", SHAPER_TYPES,
        index=SHAPER_TYPES.index(default_vals["shaper_type_x"]) if default_vals["shaper_type_x"] in SHAPER_TYPES else 0,
    )
    sh_freq_x = st.number_input("Частота X (Гц)", value=float(default_vals["shaper_freq_x"]), min_value=0.0, step=0.1, format="%.1f")
    sh_type_y = st.selectbox(
        "Тип шейпера Y", SHAPER_TYPES,
        index=SHAPER_TYPES.index(default_vals["shaper_type_y"]) if default_vals["shaper_type_y"] in SHAPER_TYPES else 0,
    )
    sh_freq_y = st.number_input("Частота Y (Гц)", value=float(default_vals["shaper_freq_y"]), min_value=0.0, step=0.1, format="%.1f")

data_input = st.text_area("Mesh Points:", value=default_vals["points"], height=100)

if st.button("🚀 ВИЗУАЛИЗИРОВАТЬ", use_container_width=True):
    if data_input:
        nums = [float(n) for n in re.findall(r"[-+]?\d*\.\d+|\d+", data_input)]
        if len(nums) < grid_x * grid_y:
            st.error(f"Нужно {grid_x * grid_y} точек. Найдено: {len(nums)}")
        else:
            matrix = np.array(nums[:grid_x*grid_y]).reshape((grid_y, grid_x))
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
        # --- Анализ сетки ---
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

        # --- Настройка винтов/валов ---
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

        st.divider()

        # --- Блок шейпера ---
        st.write("### ⚡ Шейпер: ускорения")
        if sh_freq_x > 0 and sh_freq_y > 0:
            kx = SHAPER_K.get(sh_type_x)
            ky = SHAPER_K.get(sh_type_y)
            if kx and ky:
                accel_x = kx * sh_freq_x ** 2
                accel_y = ky * sh_freq_y ** 2
                rec = int(min(accel_x, accel_y) / 500) * 500
                limit_axis = "X" if accel_x < accel_y else "Y"

                sc1, sc2 = st.columns(2)
                sc1.metric(f"X  {sh_type_x.upper()}", f"{sh_freq_x:.1f} Гц", f"≤ {accel_x:.0f} мм/с²")
                sc2.metric(f"Y  {sh_type_y.upper()}", f"{sh_freq_y:.1f} Гц", f"≤ {accel_y:.0f} мм/с²")

                st.markdown(
                    f"""
                    <div style="background:#1a2a1a;border:1px solid #2d5a2d;border-radius:8px;padding:12px 16px;margin-top:8px">
                        <div style="color:#9ca3af;font-size:0.8rem">лимит: ось {limit_axis}</div>
                        <div style="color:#4ade80;font-size:2rem;font-weight:700;line-height:1.2">≤ {rec} мм/с²</div>
                        <div style="color:#6b7280;font-size:0.75rem">рекомендованное max_accel</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            else:
                st.warning("Неизвестный тип шейпера.")
        else:
            st.info("Укажите частоты шейпера X и Y в боковой панели.")
