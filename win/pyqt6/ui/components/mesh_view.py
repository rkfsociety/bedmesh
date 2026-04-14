import numpy as np
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt6.QtGui import QImage, QPixmap, QPainter, QFont, QColor
from PyQt6.QtCore import Qt
from core.mesh_parser import BedMeshData

class MeshView(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        self.label = QLabel()
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setStyleSheet("background-color: #1e1e1e;")
        layout.addWidget(self.label)

        self.data = None

    def update_mesh(self, data: BedMeshData):
        self.data = data
        self._render_image()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.data:
            self._render_image()

    def _render_image(self):
        if not self.data:
            return

        z = self.data.z
        h, w = z.shape
        z_min, z_max = z.min(), z.max()

        # Вычисляем доступное пространство внутри вкладки
        avail_w = self.width() - 20
        avail_h = self.height() - 20
        if avail_w <= 0 or avail_h <= 0:
            return

        # Динамический размер ячейки, чтобы сетка влезала в окно
        cell_size = min(avail_w / w, avail_h / h)
        cell_size = max(20, int(cell_size))

        # Нормализация для цвета
        if z_max == z_min:
            norm_z = np.zeros_like(z)
        else:
            norm_z = (z - z_min) / (z_max - z_min)

        # Палитра Синий -> Белый -> Красный
        r = np.where(norm_z < 0.5, 0, (2 * norm_z - 1) * 255)
        g = np.where(norm_z < 0.5, (2 * norm_z) * 255, (2 - 2 * norm_z) * 255)
        b = np.where(norm_z < 0.5, (2 * (1 - norm_z)) * 255, 0)

        rgb = np.stack([r, g, b], axis=-1).astype(np.uint8)
        scaled_rgb = np.repeat(np.repeat(rgb, cell_size, axis=0), cell_size, axis=1).copy()

        img_h, img_w, _ = scaled_rgb.shape
        q_img = QImage(scaled_rgb.data, img_w, img_h, img_w * 3, QImage.Format.Format_RGB888)
        pixmap = QPixmap.fromImage(q_img)

        # Рисуем значения
        painter = QPainter(pixmap)
        painter.setFont(QFont("Consolas", int(cell_size * 0.35), QFont.Weight.Bold))

        for i in range(h):
            for j in range(w):
                val = z[i, j]
                txt = f"{val:+.3f}"
                norm = norm_z[i, j]
                painter.setPen(QColor(0,0,0) if 0.3 < norm < 0.7 else QColor(255,255,255))

                cx = j * cell_size + cell_size // 2
                cy = i * cell_size + cell_size // 2
                fm = painter.fontMetrics()
                rect = fm.boundingRect(txt)
                painter.drawText(cx - rect.width() // 2, cy + rect.height() // 3, txt)

        # Оси координат
        painter.setPen(QColor(150, 150, 150))
        painter.setFont(QFont("Arial", max(8, int(cell_size * 0.25))))
        for j in range(w + 1):
            x_val = self.data.min_x + j * (self.data.max_x - self.data.min_x) / w
            painter.drawText(j * cell_size + 2, img_h + 15, f"{int(x_val)}")
        for i in range(h + 1):
            y_val = self.data.min_y + i * (self.data.max_y - self.data.min_y) / h
            painter.drawText(2, i * cell_size + cell_size // 3, f"{int(y_val)}")

        painter.end()
        self.label.setPixmap(pixmap)