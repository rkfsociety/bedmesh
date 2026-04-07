import streamlit as st
import plotly.graph_objects as go
import numpy as np
import re

# Настройка страницы
st.set_page_config(page_title="Bed Mesh Interactive", layout="wide")

st.title("🔄 Интерактивный Bed Mesh Visualizer")
st.markdown("Вставьте данные, и вы сможете вращать карту мышкой.")

# Боковая панель
st.sidebar.header("Настройки сетки")
grid_x = st.sidebar.number_input("Точек по X", min_value=2, max_value=20, value=5)
grid_y = st.sidebar.number_input("Точек по Y", min_value=2, max_value=20, value=5)

# Ввод данных
data_input = st.text_area("Данные из консоли:", height=200)

if st.button("ПОСТРОИТЬ ИНТЕРАКТИВНУЮ КАРТУ"):
    if data_input:
        raw_nums = re.findall(r"[-+]?\d*\.\d+|\d+", data_input)
        nums = [float(n) for n in raw_nums]
        
        total = grid_x * grid_y
        if len(nums) < total:
            st.error(f"Нужно {total} точек, найдено {len(nums)}")
        else:
            matrix = np.array(nums[:total]).reshape((grid_y, grid_x))
            
            # Создаем интерактивный график Plotly
            fig = go.Figure(data=[go.Surface(
                z=matrix,
                colorscale='RdYlBu_r',  # Стиль Klipper
                colorbar=dict(title='Z (мм)')
            )])

            fig.update_layout(
                title=f'Карта стола {grid_x}x{grid_y}',
                autosize=True,
                width=800,
                height=800,
                scene=dict(
                    xaxis_title='X (точки)',
                    yaxis_title='Y (точки)',
                    zaxis_title='Z (мм)',
                    aspectmode='manual',
                    aspectratio=dict(x=1, y=1, z=0.5) # Немного приплюснем по Z для наглядности
                )
            )

            # Вывод интерактивного графика
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Жду данные для обработки...")