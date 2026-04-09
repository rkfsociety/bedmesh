import plotly.graph_objects as go
import plotly.io as pio
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.patheffects as path_effects
import os

BG_COLOR = "#1a1a1a"

def clear_tab(tab):
    """Очистка вкладки"""
    for w in tab.winfo_children():
        w.destroy()

def draw_2d_map(tab, matrix, bx, by, gx, gy):
    """Стандартная 2D карта (CPU)"""
    clear_tab(tab)
    plt.style.use('dark_background')
    fig = plt.figure(figsize=(6, 6), dpi=100)
    fig.patch.set_facecolor(BG_COLOR)
    ax = fig.add_subplot(111)
    ax.set_facecolor(BG_COLOR)
    
    xe, ye = np.linspace(0, bx, gx + 1), np.linspace(0, by, gy + 1)
    ax.pcolormesh(xe, ye, matrix, cmap='RdYlBu_r', edgecolors='#222222', linewidth=0.5)
    
    xc, yc = (xe[:-1] + xe[1:]) / 2, (ye[:-1] + ye[1:]) / 2
    for i in range(gy):
        for j in range(gx):
            t = ax.text(xc[j], yc[i], f"{matrix[i,j]:.3f}", ha="center", va="center", 
                        fontweight='bold', color="white", fontsize=8)
            t.set_path_effects([path_effects.withStroke(linewidth=2, foreground="black")])
    
    ax.set_aspect('equal')
    canvas = FigureCanvasTkAgg(fig, master=tab)
    canvas.draw()
    canvas.get_tk_widget().pack(fill="both", expand=True)

def save_plotly_html(matrix, bx, by, gx, gy):
    """Генерация HTML файла для 3D карты (GPU WebGL)"""
    x = np.linspace(0, bx, gx)
    y = np.linspace(0, by, gy)
    
    fig = go.Figure(data=[go.Surface(
        z=matrix, x=x, y=y,
        colorscale='RdYlBu',
        reversescale=True,
        contours_z=dict(show=True, usecolormap=True, highlightcolor="white", project_z=True),
        lighting=dict(ambient=0.5, diffuse=0.8, roughness=0.1, specular=1.5)
    )])

    fig.update_layout(
        template="plotly_dark",
        margin=dict(l=0, r=0, b=0, t=0),
        scene=dict(
            xaxis=dict(title='X (mm)', gridcolor='rgb(60,60,60)'),
            yaxis=dict(title='Y (mm)', gridcolor='rgb(60,60,60)'),
            zaxis=dict(title='Z (mm)', gridcolor='rgb(60,60,60)', range=[-2, 2]),
            aspectratio=dict(x=1, y=1, z=0.4),
        ),
        paper_bgcolor=BG_COLOR,
        plot_bgcolor=BG_COLOR
    )
    
    # Сохраняем во временный файл, так как WebView2 лучше работает с файлами
    path = os.path.abspath("temp_mesh.html")
    pio.write_html(fig, file=path, auto_open=False, include_plotlyjs='cdn')
    return path