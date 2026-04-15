import numpy as np
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QApplication, QSizePolicy
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
        # Prevent layout feedback loop: QLabel's sizeHint depends on pixmap size.
        # If we keep scaling pixmap to label size, the label may grow to fit the pixmap, triggering endless growth.
        self.label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Ignored)
        self.label.setMinimumSize(1, 1)
        layout.addWidget(self.label)

        self._pixmap = None

    def update_mesh(self, data: BedMeshData):
        # 1. Подготовка LUT (палитра)
        lut = self._build_lut()
        z = data.z
        # Для bed_mesh важнее показывать отклонения относительно нуля.
        # Делаем симметричную нормализацию вокруг 0: синий (<0) — белый (≈0) — красный (>0).
        z_min, z_max = float(z.min()), float(z.max())
        span = max(abs(z_min), abs(z_max), 1e-9)
        norm = (z / span + 1.0) * 0.5
        norm = np.clip(norm, 0.0, 1.0)
        idx = (norm * 255).astype(np.uint8)

        # 2. Создание изображения
        size = 780
        pad = 16
        cell_w = size / data.x_count
        cell_h = size / data.y_count

        img = QImage(size + pad * 2, size + pad * 2, QImage.Format.Format_ARGB32)
        img.fill(QColor("#121212"))

        painter = QPainter(img)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        font = QFont("Segoe UI", 10, QFont.Weight.DemiBold)
        painter.setFont(font)

        # Фон под сетку (чтобы края выглядели аккуратнее)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#1a1a1a"))
        painter.drawRoundedRect(QRectF(pad - 2, pad - 2, size + 4, size + 4), 10, 10)

        # 3. Отрисовка ячеек, сетки и текста
        # В системе координат принтера (0,0) считается слева снизу,
        # а в координатах изображения (0,0) — слева сверху. Инвертируем Y.
        for i in range(data.y_count):
            y = (data.y_count - 1 - i) * cell_h
            for j in range(data.x_count):
                val = data.z[i, j]
                rgb = lut[idx[i, j]][:3]
                color = QColor(int(rgb[0]), int(rgb[1]), int(rgb[2]))
                rect = QRectF(pad + j * cell_w, pad + y, cell_w, cell_h)

                painter.fillRect(rect, color)
                painter.setPen(QColor("#262626"))
                painter.drawRect(rect)

                sign = "+" if val >= 0 else ""
                text = f"{sign}{val:.3f}"

                # Текст всегда читаемый: мягкая тень + основной цвет (по яркости ячейки).
                lum = 0.2126 * color.red() + 0.7152 * color.green() + 0.0722 * color.blue()
                main = QColor("#0f0f0f") if lum > 150 else QColor("#f6f6f6")
                shadow = QColor(0, 0, 0, 140) if lum > 150 else QColor(255, 255, 255, 90)

                # Тень: лёгкий смещённый дубль
                painter.setPen(shadow)
                painter.drawText(rect.translated(0.8, 0.8), Qt.AlignmentFlag.AlignCenter, text)

                # Лёгкая “обводка” (4 направления) для стабильной читаемости
                outline = QColor(0, 0, 0, 110) if main.lightness() > 128 else QColor(255, 255, 255, 70)
                painter.setPen(outline)
                painter.drawText(rect.translated(-0.6, 0), Qt.AlignmentFlag.AlignCenter, text)
                painter.drawText(rect.translated(0.6, 0), Qt.AlignmentFlag.AlignCenter, text)
                painter.drawText(rect.translated(0, -0.6), Qt.AlignmentFlag.AlignCenter, text)
                painter.drawText(rect.translated(0, 0.6), Qt.AlignmentFlag.AlignCenter, text)

                painter.setPen(main)
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

    def _build_lut(self):
        lut = np.zeros((256, 4), dtype=np.uint8)
        # Контрастная, но мягкая diverging‑палитра (синий → белый → красный).
        # Так карта остаётся “читаемой”, и глаза не устают.
        colors = [
            (35, 87, 150),    # синий
            (120, 175, 215),  # голубой
            (248, 248, 248),  # белый
            (245, 160, 140),  # светло-красный
            (185, 60, 55),    # красный
        ]
        pos = [0, 64, 128, 192, 255]
        for c in range(3):
            lut[:, c] = np.interp(np.arange(256), pos, [x[c] for x in colors])
        lut[:, 3] = 255  # Alpha
        return lut

    def copy_to_clipboard(self):
        if self._pixmap:
            QApplication.clipboard().setPixmap(self._pixmap)