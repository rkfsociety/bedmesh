from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QVector3D
import pyqtgraph.opengl as gl

from ui.components.mesh_3d_math import CameraFit, clamp_zoom_distance


class Mesh3DGLView(gl.GLViewWidget):
    """GL view with stable mouse gestures for the bed mesh scene."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._mouse_position = None
        self._home_fit: CameraFit | None = None

    def set_home_view(self, fit: CameraFit, reset: bool) -> None:
        self._home_fit = fit
        if reset:
            self.reset_camera()

    def reset_camera(self) -> None:
        if self._home_fit is None:
            return
        self.opts["center"] = QVector3D(*self._home_fit.center)
        self.opts["distance"] = self._home_fit.distance
        self.opts["azimuth"] = -60.0
        self.opts["elevation"] = 25.0
        self.update()

    def mousePressEvent(self, event):
        self._mouse_position = event.position()
        event.accept()

    def mouseMoveEvent(self, event):
        current = event.position()
        if self._mouse_position is None:
            self._mouse_position = current
        delta = current - self._mouse_position
        self._mouse_position = current

        if event.buttons() & Qt.MouseButton.LeftButton:
            self.orbit(-delta.x(), delta.y())
        elif event.buttons() & Qt.MouseButton.RightButton:
            self.pan(delta.x(), delta.y(), 0, relative="view")
        event.accept()

    def wheelEvent(self, event):
        if self._home_fit is None:
            return super().wheelEvent(event)
        delta = event.angleDelta().x() or event.angleDelta().y()
        self.opts["distance"] = clamp_zoom_distance(
            self.opts["distance"],
            delta,
            self._home_fit.minimum_distance,
            self._home_fit.maximum_distance,
        )
        self.update()
        event.accept()

    def mouseDoubleClickEvent(self, event):
        self.reset_camera()
        event.accept()
