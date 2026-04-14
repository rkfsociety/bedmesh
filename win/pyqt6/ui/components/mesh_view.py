import pyqtgraph as pg
from PyQt6.QtWidgets import QWidget, QVBoxLayout
from PyQt6.QtGui import QFont
from core.mesh_parser import BedMeshData

class MeshView(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        self.view = pg.GraphicsLayoutWidget()
        layout.addWidget(self.view)
        self.view.clear()

        # 🎨 Палитра: Синий -> Белый -> Красный (как в Mainsail/Klipper)
        cmap_pos = [0.0, 0.25, 0.5, 0.75, 1.0]
        cmap_col = [
            pg.mkColor('#0000FF'), # Глубокий синий (минус)
            pg.mkColor('#8080FF'), # Светло-синий
            pg.mkColor('#FFFFFF'), # Белый (ноль)
            pg.mkColor('#FF8080'), # Светло-красный
            pg.mkColor('#FF0000')  # Глубокий красный (плюс)
        ]
        self.custom_cmap = pg.ColorMap(pos=cmap_pos, color=cmap_col)

        # Цветовая шкала СПРАВА
        self.colorbar = pg.ColorBarItem(
            values=(-0.5, 0.5),
            colorMap=self.custom_cmap,
            label='Отклонение (мм)'
        )

        # График
        self.plot = self.view.addPlot(row=0, col=0)
        self.plot.setAspectLocked(True)
        self.plot.showGrid(x=True, y=True, alpha=0.5)
        self.plot.setLabels(left="Ось Y (мм)", bottom="Ось X (мм)")
        self.plot.setMouseEnabled(x=False, y=False) # 🔒 Фиксация карты

        self.img = pg.ImageItem()
        self.plot.addItem(self.img)
        self.colorbar.setImageItem(self.img)
        self.view.addItem(self.colorbar, row=0, col=1)

        self.text_items = []

    def update_mesh(self, data: BedMeshData):
        # Очистка старых меток
        for item in self.text_items:
            self.plot.removeItem(item)
        self.text_items.clear()

        # Отрисовка карты
        self.img.setImage(data.z)
        x_range = data.max_x - data.min_x
        y_range = data.max_y - data.min_y
        self.img.setRect(data.min_x, data.min_y, x_range, y_range)

        # Автоматическая настройка цветового диапазона
        z_min, z_max = data.z.min(), data.z.max()
        margin = (z_max - z_min) * 0.05  # Небольшой отступ, чтобы цвета не "съедались" на краях
        self.colorbar.setLevels([z_min - margin, z_max + margin])

        self.plot.setXRange(data.min_x, data.max_x, padding=0.05)
        self.plot.setYRange(data.min_y, data.max_y, padding=0.05)

        dx = x_range / data.x_count
        dy = y_range / data.y_count

        # Рисуем значения в ячейках
        for i in range(data.y_count):
            for j in range(data.x_count):
                val = data.z[i, j]
                sign = "+" if val >= 0 else ""
                text_str = f"{sign}{val:.3f}"
                cx = data.min_x + j * dx + dx / 2
                cy = data.min_y + i * dy + dy / 2

                # Адаптивный цвет текста для читаемости на любом фоне
                ratio = (val - z_min) / (z_max - z_min + 1e-9)
                txt_color = "black" if 0.25 < ratio < 0.75 else "white"
                
                text_item = pg.TextItem(text_str, anchor=(0.5, 0.5), color=txt_color)
                text_item.setFont(QFont("Consolas", 9, QFont.Weight.Bold))
                text_item.setPos(cx, cy)
                
                self.plot.addItem(text_item)
                self.text_items.append(text_item)