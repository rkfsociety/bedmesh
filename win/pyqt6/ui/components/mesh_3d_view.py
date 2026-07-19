from __future__ import annotations

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt6.QtCore import Qt

from core.mesh_parser import BedMeshData
from ui.components.mesh_3d_math import colors_from_z, scaled_z

# pyqtgraph/OpenGL импортируются лениво внутри ensure_ready()


class Mesh3DView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._palette_key = "soft"
        self._data: BedMeshData | None = None
        self._gl_view = None
        self._surface = None
        self._ready = False
        self._failed = False

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
            self.update_mesh(self._data)

    def ensure_ready(self) -> bool:
        if self._ready:
            return True
        if self._failed:
            return False
        try:
            import numpy as np
            import pyqtgraph.opengl as gl  # noqa: WPS433

            view = gl.GLViewWidget()
            view.setBackgroundColor((30, 30, 30))
            view.opts["distance"] = 40
            view.opts["elevation"] = 25
            view.opts["azimuth"] = -60

            grid = gl.GLGridItem()
            grid.setSize(x=20, y=20)
            grid.setSpacing(x=1, y=1)
            view.addItem(grid)

            # Пустая поверхность; данные придут в update_mesh.
            # GLSurfacePlotItem ждёт z shape (len(x), len(y)).
            z0 = np.zeros((2, 2))
            surface = gl.GLSurfacePlotItem(
                z=z0,
                shader="shaded",
                smooth=False,
                computeNormals=True,
            )
            view.addItem(surface)

            self._layout.removeWidget(self._placeholder)
            self._placeholder.hide()
            self._layout.addWidget(view)
            self._gl_view = view
            self._surface = surface
            self._ready = True
            if self._data is not None:
                self.update_mesh(self._data)
            return True
        except Exception as e:
            self._failed = True
            self._placeholder.setText(f"3D недоступен:\n{e}")
            return False

    def update_mesh(self, data: BedMeshData) -> None:
        self._data = data
        if not self._ready or self._surface is None:
            return
        import numpy as np
        from pyqtgraph import Vector

        z = np.asarray(data.z, dtype=float)  # (ny, nx)
        z_vis = scaled_z(z)
        cols = colors_from_z(z, self._palette_key)  # (ny, nx, 4)

        x = np.asarray(data.x, dtype=float)
        y = np.asarray(data.y, dtype=float)
        x_c = x - float(np.mean(x))
        y_c = y - float(np.mean(y))

        # API: z/colors shape (len(x), len(y)) == (nx, ny)
        self._surface.setData(
            x=x_c,
            y=y_c,
            z=z_vis.T,
            colors=np.transpose(cols, (1, 0, 2)),
        )

        span = max(float(np.ptp(x)), float(np.ptp(y)), 1.0)
        if self._gl_view is not None:
            self._gl_view.opts["distance"] = span * 1.8
            self._gl_view.opts["center"] = Vector(0, 0, float(np.mean(z_vis)))
            self._gl_view.update()
