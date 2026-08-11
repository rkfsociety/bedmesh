from __future__ import annotations

import numpy as np
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt6.QtCore import Qt

from core.mesh_parser import BedMeshData
from ui.components.mesh_3d_math import fit_camera, prepare_surface
from utils.logger import get_logger

# pyqtgraph/OpenGL импортируются лениво внутри ensure_ready()


class Mesh3DView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._palette_key = "soft"
        self._data: BedMeshData | None = None
        self._gl_view = None
        self._grid = None
        self._axis = None
        self._coordinate_labels = []
        self._surface = None
        self._gl = None
        self._ready = False
        self._failed = False
        self._logger = get_logger(__name__)

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._placeholder = QLabel("3D: не инициализировано")
        self._placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._placeholder.setStyleSheet("background: #1e1e1e; color: #888; border: 1px solid #444;")
        self._layout.addWidget(self._placeholder)

    def is_ready(self) -> bool:
        return self._ready

    def set_palette(self, palette_key: str) -> None:
        self._palette_key = palette_key or "classic"
        if self._ready and self._data is not None:
            self.update_mesh(self._data, reset_camera=False)

    def ensure_ready(self) -> bool:
        if self._ready:
            return True
        if self._failed:
            return False
        try:
            import pyqtgraph.opengl as gl  # noqa: WPS433
            from ui.components.mesh_3d_camera import Mesh3DGLView

            view = Mesh3DGLView()
            view.setBackgroundColor((30, 30, 30))

            grid = gl.GLGridItem()
            view.addItem(grid)
            axis = gl.GLAxisItem()
            view.addItem(axis)
            view.hide()
            self._layout.addWidget(view)
            self._gl = gl
            self._gl_view = view
            self._grid = grid
            self._axis = axis
            self._surface = None
            self._ready = True
            self._placeholder.setText("3D: нет данных")
            if self._data is not None:
                self.update_mesh(self._data)
            return True
        except Exception as e:
            self._failed = True
            self._placeholder.setText(f"3D недоступен:\n{e}")
            return False

    def update_mesh(self, data: BedMeshData, *, reset_camera: bool = True) -> None:
        self._data = data
        if not self._ready or self._gl_view is None or self._grid is None:
            return
        try:
            payload = prepare_surface(
                data.x,
                data.y,
                data.z,
                self._palette_key,
                bed_bounds=self._bed_bounds(data),
            )
            if self._surface is None:
                self._surface = self._gl.GLSurfacePlotItem(
                    shader="shaded",
                    smooth=False,
                    computeNormals=True,
                )
                self._gl_view.addItem(self._surface)
            self._surface.setData(
                x=payload.x,
                y=payload.y,
                z=payload.z,
                colors=payload.colors,
            )
            self._grid.setSize(x=payload.span_x, y=payload.span_y)
            self._grid.setSpacing(x=payload.spacing_x, y=payload.spacing_y)
            self._update_coordinate_axes(data, payload)
            self._gl_view.set_home_view(fit_camera(payload), reset=reset_camera)
            self._placeholder.hide()
            self._gl_view.show()
            self._gl_view.update()
        except Exception as exc:
            self._logger.exception("Не удалось обновить 3D-карту")
            self._gl_view.hide()
            self._placeholder.setText(f"3D недоступен:\n{exc}")
            self._placeholder.show()

    def _update_coordinate_axes(self, data: BedMeshData, payload) -> None:
        if self._axis is None or self._gl is None or self._gl_view is None:
            return

        # Оси располагаются в нижнем углу поверхности. Z здесь визуальный,
        # поэтому физические координаты подписываем только для X/Y.
        z_floor = float(np.min(payload.z)) - max(payload.span_x, payload.span_y) * 0.08
        axis_offset = max(payload.span_x, payload.span_y) * 0.08
        self._axis.setSize(
            x=payload.span_x,
            y=payload.span_y,
            z=max(payload.span_x, payload.span_y) * 0.18,
        )
        self._axis.resetTransform()
        self._axis.translate(
            -payload.span_x / 2.0,
            -payload.span_y / 2.0,
            z_floor,
        )

        for label in self._coordinate_labels:
            self._gl_view.removeItem(label)
        self._coordinate_labels = []

        def add_label(text: str, pos: tuple[float, float, float]) -> None:
            label = self._gl.GLTextItem(
                pos=pos,
                text=text,
                color=(220, 220, 220, 230),
            )
            self._gl_view.addItem(label)
            self._coordinate_labels.append(label)

        bed_min_x, bed_max_x, bed_min_y, bed_max_y = self._bed_bounds(data)
        x_center = (bed_min_x + bed_max_x) / 2.0
        y_center = (bed_min_y + bed_max_y) / 2.0
        x_ticks = np.linspace(bed_min_x, bed_max_x, 5)
        y_ticks = np.linspace(bed_min_y, bed_max_y, 5)
        for value in x_ticks:
            x = float(value - x_center)
            add_label(
                f"{value:g}",
                (x, -payload.span_y / 2.0 - axis_offset, z_floor),
            )
        for value in y_ticks:
            y = float(value - y_center)
            add_label(
                f"{value:g}",
                (-payload.span_x / 2.0 - axis_offset, y, z_floor),
            )

        add_label(
            "X (мм)",
            (payload.span_x / 2.0 + axis_offset, -payload.span_y / 2.0 - axis_offset, z_floor),
        )
        add_label(
            "Y (мм)",
            (-payload.span_x / 2.0 - axis_offset, payload.span_y / 2.0 + axis_offset, z_floor),
        )

    @staticmethod
    def _bed_bounds(data: BedMeshData) -> tuple[float, float, float, float]:
        """Возвращает рабочую область, либо границы mesh для старых форматов."""
        if data.bed_min_x is None or data.bed_max_x is None:
            min_x, max_x = data.min_x, data.max_x
        else:
            min_x, max_x = data.bed_min_x, data.bed_max_x
        if data.bed_min_y is None or data.bed_max_y is None:
            min_y, max_y = data.min_y, data.max_y
        else:
            min_y, max_y = data.bed_min_y, data.bed_max_y
        return min_x, max_x, min_y, max_y
