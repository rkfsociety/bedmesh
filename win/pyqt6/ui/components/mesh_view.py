import numpy as np
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QApplication
from PyQt6.QtGui import QPixmap, QImage, QPainter, QFont, QColor
from PyQt6.QtCore import Qt, QRectF
from core.mesh_parser import BedMeshData

class MeshView(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.label = QLabel()
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setStyleSheet("background: #1e1e1e; border: 1px solid #444;")
        layout.addWidget(self.label)

        self._pixmap = None

    def update_mesh(self, data: BedMeshData):  # ✅ ИСПРАВЛЕНО: добавлено 'data:'
        # 1. Подготовка LUT (палитра)
        lut = self._build_lut()
        z = data.z
        z_min, z_max = z.min(), z.max()
        norm = (z - z_min) / (z_max - z_min + 1e-9)
        idx = (norm * 255).astype(np.uint8)

        # 2. Создание изображения 700x700
        size = 700
        cell_w = size / data.x_count
        cell_h = size / data.y_count

        img = QImage(size, size, QImage.Format.Format_ARGB32)
        img.fill(QColor("#2b2b2b"))

        painter = QPainter(img)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        font = QFont("Consolas", 11, QFont.Weight.Bold)
        painter.setFont(font)

        # 3. Отрисовка ячеек, сетки и текста
        for i in range(data.y_count):
            for j in range(data.x_count):
                val = data.z[i, j]
                color = QColor(*lut[idx[i, j]][:3])
                rect = QRectF(j * cell_w, i * cell_h, cell_w, cell_h)

                painter.fillRect(rect, color)
                painter.setPen(QColor(80, 80, 80))
                painter.drawRect(rect)

                sign = "+" if val >= 0 else ""
                ratio = (val - z_min) / (z_max - z_min + 1e-9)
                txt_color = QColor("black") if 0.25 < ratio < 0.75 else QColor("white")
                painter.setPen(txt_color)
                painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, f"{sign}{val:.3f}")

        painter.end()

        self._pixmap = QPixmap.fromImage(img)
        self.label.setPixmap(self._pixmap.scaled(
            self.label.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation
        ))

    def _build_lut(self):
        lut = np.zeros((256, 4), dtype=np.uint8)
        colors = [(0,0,255), (128,128,255), (255,255,255), (255,128,128), (255,0,0)]
        pos = [0, 64, 128, 192, 255]
        for c in range(3):
            lut[:, c] = np.interp(np.arange(256), pos, [x[c] for x in colors])
        lut[:, 3] = 255  # Alpha
        return lut

    def copy_to_clipboard(self):
        if self._pixmap:
            QApplication.clipboard().setPixmap(self._pixmap)
