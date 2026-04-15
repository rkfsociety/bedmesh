import numpy as np
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QApplication, QSizePolicy
from PyQt6.QtGui import QPixmap, QImage, QPainter, QFont, QColor
from PyQt6.QtCore import Qt, QRectF
from core.mesh_parser import BedMeshData
from ui.components.palettes import build_lut

class MeshView(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.label = QLabel()
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setStyleSheet("background: #1e1e1e; border: 1px solid #444;")
        # Prevent layout feedback loop: QLabel's sizeHint depends on pixmap size.
        # If we keep scaling pixmap to label size, the label may grow to fit the pixmap, triggering endless growth.
        self.label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Ignored)
        self.label.setMinimumSize(1, 1)
        layout.addWidget(self.label)

        self._pixmap = None
        self._palette_key = "soft"

    def set_palette(self, palette_key: str):
        self._palette_key = palette_key or "classic"

    def update_mesh(self, data: BedMeshData):
        lut = build_lut(self._palette_key)
        z = data.z
        z_min, z_max = z.min(), z.max()
        norm = (z - z_min) / (z_max - z_min + 1e-9)
        idx = (norm * 255).astype(np.uint8)

        # 2) Создание изображения
        size = 700
        cell_w = size / data.x_count
        cell_h = size / data.y_count

        img = QImage(size, size, QImage.Format.Format_ARGB32)
        img.fill(QColor("#2b2b2b"))

        painter = QPainter(img)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setFont(QFont("Consolas", 11, QFont.Weight.Bold))

        # 3) Отрисовка ячеек, сетки и текста
        # В системе координат принтера (0,0) считается слева снизу,
        # а в координатах изображения (0,0) — слева сверху. Инвертируем Y.
        for i in range(data.y_count):
            y = (data.y_count - 1 - i) * cell_h
            for j in range(data.x_count):
                val = data.z[i, j]
                color = QColor(*lut[idx[i, j]][:3])
                rect = QRectF(j * cell_w, y, cell_w, cell_h)

                painter.fillRect(rect, color)
                painter.setPen(QColor(80, 80, 80))
                painter.drawRect(rect)

                sign = "+" if val >= 0 else ""
                text = f"{sign}{val:.3f}"

                ratio = (val - z_min) / (z_max - z_min + 1e-9)
                txt_color = QColor("black") if 0.25 < ratio < 0.75 else QColor("white")
                painter.setPen(txt_color)
                painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, text)

        painter.end()

        self._pixmap = QPixmap.fromImage(img)
        self._rescale_to_label()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._rescale_to_label()

    def _rescale_to_label(self):
        if not self._pixmap:
            return
        target = self.label.contentsRect().size()
        if target.width() <= 0 or target.height() <= 0:
            return
        self.label.setPixmap(self._pixmap.scaled(
            target,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        ))

    def copy_to_clipboard(self):
        if self._pixmap:
            QApplication.clipboard().setPixmap(self._pixmap)