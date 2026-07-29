import numpy as np
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QApplication, QSizePolicy
from PyQt6.QtGui import QPixmap, QImage, QPainter, QFont, QFontMetrics, QColor
from PyQt6.QtCore import Qt, QRectF, pyqtSignal
from core.mesh_parser import BedMeshData
from ui.components.mesh_2d_layout import (
    choose_label_font_px,
    mesh_index_at_position,
)
from ui.components.palettes import build_lut


class _MeshLabel(QLabel):
    mouse_position_changed = pyqtSignal(float, float)

    def __init__(self):
        super().__init__()
        self.setMouseTracking(True)

    def mouseMoveEvent(self, event):
        position = event.position()
        self.mouse_position_changed.emit(position.x(), position.y())
        super().mouseMoveEvent(event)


class MeshView(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.label = _MeshLabel()
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setStyleSheet("background: #1e1e1e; border: 1px solid #444;")
        # Prevent layout feedback loop: QLabel's sizeHint depends on pixmap size.
        # If we keep scaling pixmap to label size, the label may grow to fit the pixmap, triggering endless growth.
        self.label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Ignored)
        self.label.setMinimumSize(1, 1)
        self.label.mouse_position_changed.connect(self._on_mouse_position_changed)
        layout.addWidget(self.label)

        self._pixmap = None
        self._data = None
        self._palette_key = "soft"
        self._screen_labels_visible = False
        self._last_render_labels_visible = False

    def set_palette(self, palette_key: str):
        self._palette_key = palette_key or "classic"

    def update_mesh(self, data: BedMeshData):
        self._data = data
        self._pixmap = self.render_mesh(data, 700, 700)
        self._screen_labels_visible = self._last_render_labels_visible
        self._rescale_to_label()

    def render_mesh(
        self,
        data: BedMeshData,
        width: int,
        height: int,
        force_labels: bool = False,
    ) -> QPixmap:
        lut = build_lut(self._palette_key)
        z = data.z
        z_min, z_max = z.min(), z.max()
        norm = (z - z_min) / (z_max - z_min + 1e-9)
        idx = (norm * 255).astype(np.uint8)

        cell_w = width / data.x_count
        cell_h = height / data.y_count

        img = QImage(width, height, QImage.Format.Format_ARGB32)
        img.fill(QColor("#2b2b2b"))

        painter = QPainter(img)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        preferred_font_px = 15
        font = QFont("Consolas")
        font.setWeight(QFont.Weight.Bold)
        font.setPixelSize(preferred_font_px)
        metrics = QFontMetrics(font)
        font_px = choose_label_font_px(
            cell_w,
            cell_h,
            metrics.horizontalAdvance("+0.000"),
            metrics.height(),
            preferred_px=preferred_font_px,
        )
        if force_labels and font_px is None:
            font_px = 7
        labels_visible = font_px is not None
        if labels_visible:
            font.setPixelSize(font_px)
            painter.setFont(font)
        self._last_render_labels_visible = labels_visible

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

                if labels_visible:
                    text = f"{val:+.3f}"
                    ratio = (val - z_min) / (z_max - z_min + 1e-9)
                    txt_color = QColor("black") if 0.25 < ratio < 0.75 else QColor("white")
                    painter.setPen(txt_color)
                    painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, text)

        painter.end()
        return QPixmap.fromImage(img)

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

    def tooltip_for_position(self, x: float, y: float) -> str | None:
        if self._data is None:
            return None
        pixmap = self.label.pixmap()
        if pixmap is None or pixmap.isNull():
            return None

        index = mesh_index_at_position(
            x,
            y,
            self.label.contentsRect().width(),
            self.label.contentsRect().height(),
            pixmap.width(),
            pixmap.height(),
            self._data.x_count,
            self._data.y_count,
        )
        if index is None:
            return None

        row, column = index
        return (
            f"Точка [{row}, {column}]\n"
            f"X: {self._data.x[column]:.3f} мм\n"
            f"Y: {self._data.y[row]:.3f} мм\n"
            f"Z: {self._data.z[row, column]:+.3f} мм"
        )

    def _on_mouse_position_changed(self, x: float, y: float) -> None:
        self.label.setToolTip(self.tooltip_for_position(x, y) or "")

    def copy_to_clipboard(self):
        if self._pixmap:
            QApplication.clipboard().setPixmap(self._pixmap)
