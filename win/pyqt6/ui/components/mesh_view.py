import numpy as np
from PyQt6.QtCore import QPoint, QRectF, Qt
from PyQt6.QtGui import (
    QColor,
    QFont,
    QFontMetrics,
    QImage,
    QPainter,
    QPixmap,
    QTransform,
)
from PyQt6.QtWidgets import QApplication, QGraphicsScene, QVBoxLayout, QWidget

from core.mesh_parser import BedMeshData
from ui.components.mesh_2d_layout import (
    choose_label_font_px,
    detail_canvas_size,
    detail_zoom_threshold,
    mesh_index_at_position,
)
from ui.components.mesh_graphics_view import MeshGraphicsView
from ui.components.palettes import build_lut


class MeshView(QWidget):
    SCENE_SIZE = 700

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.graphics_view = MeshGraphicsView()
        self.graphics_view.setStyleSheet(
            "background: #1e1e1e; border: 1px solid #444;"
        )
        self.graphics_view.setRenderHints(
            QPainter.RenderHint.Antialiasing
            | QPainter.RenderHint.SmoothPixmapTransform
        )
        layout.addWidget(self.graphics_view)

        self._scene = QGraphicsScene(self)
        self._scene.setSceneRect(0, 0, self.SCENE_SIZE, self.SCENE_SIZE)
        self.graphics_view.setScene(self._scene)
        self.graphics_view.setSceneRect(self._scene.sceneRect())

        self._screen_item = self._scene.addPixmap(QPixmap())
        self._detail_item = self._scene.addPixmap(QPixmap())
        self._detail_item.setVisible(False)

        self._pixmap = None
        self._detail_pixmap_cache = None
        self._data = None
        self._palette_key = "soft"
        self._screen_labels_visible = False
        self._detail_labels_visible = False
        self._last_render_labels_visible = False
        self._detail_threshold = 1.0

        self.graphics_view.zoom_changed.connect(self._on_zoom_changed)
        self.graphics_view.scene_position_changed.connect(
            self._on_scene_position_changed
        )

    def set_palette(self, palette_key: str):
        self._palette_key = palette_key or "classic"
        if self._data is not None:
            self.update_mesh(self._data)

    def update_mesh(self, data: BedMeshData):
        self._data = data
        self._pixmap = self.render_mesh(
            data,
            self.SCENE_SIZE,
            self.SCENE_SIZE,
        )
        self._screen_labels_visible = self._last_render_labels_visible
        self._screen_item.setPixmap(self._pixmap)
        self._screen_item.setTransform(QTransform())
        self._screen_item.setVisible(True)

        self._detail_pixmap_cache = None
        self._detail_item.setPixmap(QPixmap())
        self._detail_item.setTransform(QTransform())
        self._detail_item.setVisible(False)
        self._detail_labels_visible = False
        self._detail_threshold = detail_zoom_threshold(
            data.x_count,
            data.y_count,
            scene_size=self.SCENE_SIZE,
        )
        self.graphics_view.reset_view()

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
                    txt_color = (
                        QColor("black")
                        if 0.25 < ratio < 0.75
                        else QColor("white")
                    )
                    painter.setPen(txt_color)
                    painter.drawText(
                        rect,
                        Qt.AlignmentFlag.AlignCenter,
                        text,
                    )

        painter.end()
        return QPixmap.fromImage(img)

    def _ensure_detail_item(self) -> None:
        if self._detail_pixmap_cache is not None:
            return
        pixmap = self.detail_pixmap()
        if pixmap is None:
            return

        self._detail_item.setPixmap(pixmap)
        self._detail_item.setTransform(
            QTransform.fromScale(
                self.SCENE_SIZE / pixmap.width(),
                self.SCENE_SIZE / pixmap.height(),
            )
        )
        self._detail_pixmap_cache = pixmap

    def _on_zoom_changed(self, zoom: float) -> None:
        if self._data is None:
            return
        show_detail = zoom >= self._detail_threshold
        if show_detail:
            self._ensure_detail_item()
        self._screen_item.setVisible(not show_detail)
        self._detail_item.setVisible(show_detail)

    def tooltip_for_scene_position(
        self,
        x: float,
        y: float,
    ) -> str | None:
        if self._data is None:
            return None
        index = mesh_index_at_position(
            x,
            y,
            self.SCENE_SIZE,
            self.SCENE_SIZE,
            self.SCENE_SIZE,
            self.SCENE_SIZE,
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

    def tooltip_for_position(self, x: float, y: float) -> str | None:
        scene_position = self.graphics_view.mapToScene(
            QPoint(round(x), round(y))
        )
        return self.tooltip_for_scene_position(
            scene_position.x(),
            scene_position.y(),
        )

    def _on_scene_position_changed(self, x: float, y: float) -> None:
        self.graphics_view.setToolTip(
            self.tooltip_for_scene_position(x, y) or ""
        )

    def detail_pixmap(self) -> QPixmap | None:
        if self._data is None:
            return None
        if self._detail_pixmap_cache is not None:
            return self._detail_pixmap_cache

        width, height = detail_canvas_size(
            self._data.x_count,
            self._data.y_count,
        )
        pixmap = self.render_mesh(
            self._data,
            width,
            height,
            force_labels=True,
        )
        self._detail_labels_visible = self._last_render_labels_visible
        return pixmap

    def copy_to_clipboard(self):
        pixmap = self.detail_pixmap()
        if pixmap is not None:
            QApplication.clipboard().setPixmap(pixmap)
