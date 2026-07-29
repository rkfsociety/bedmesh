from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QGraphicsView


class MeshGraphicsView(QGraphicsView):
    MIN_ZOOM = 1.0
    MAX_ZOOM = 12.0
    ZOOM_STEP = 1.25

    zoom_changed = pyqtSignal(float)
    scene_position_changed = pyqtSignal(float, float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._zoom_factor = 1.0
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setTransformationAnchor(
            QGraphicsView.ViewportAnchor.AnchorViewCenter
        )
        self.setResizeAnchor(
            QGraphicsView.ViewportAnchor.AnchorViewCenter
        )
        self.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.setMouseTracking(True)
        self.viewport().setMouseTracking(True)

    def zoom_factor(self) -> float:
        return self._zoom_factor

    def set_zoom_factor(self, value: float) -> None:
        target = min(self.MAX_ZOOM, max(self.MIN_ZOOM, float(value)))
        if target == self._zoom_factor:
            return
        ratio = target / self._zoom_factor
        self.scale(ratio, ratio)
        self._zoom_factor = target
        self.zoom_changed.emit(target)

    def reset_view(self) -> None:
        self.resetTransform()
        scene_rect = self.sceneRect()
        if not scene_rect.isEmpty():
            self.fitInView(
                scene_rect,
                Qt.AspectRatioMode.KeepAspectRatio,
            )
            self.centerOn(scene_rect.center())
        self._zoom_factor = 1.0
        self.zoom_changed.emit(self._zoom_factor)

    def wheelEvent(self, event):
        delta = event.angleDelta().y()
        position = event.position().toPoint()
        anchor_before = self.mapToScene(position)
        if delta > 0:
            self.set_zoom_factor(self._zoom_factor * self.ZOOM_STEP)
        elif delta < 0:
            self.set_zoom_factor(self._zoom_factor / self.ZOOM_STEP)
        anchor_after = self.mapToScene(position)
        center = self.mapToScene(self.viewport().rect().center())
        self.centerOn(center + anchor_before - anchor_after)
        event.accept()

    def mouseDoubleClickEvent(self, event):
        self.reset_view()
        event.accept()

    def mouseMoveEvent(self, event):
        super().mouseMoveEvent(event)
        position = self.mapToScene(event.position().toPoint())
        self.scene_position_changed.emit(position.x(), position.y())

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._zoom_factor == self.MIN_ZOOM:
            self.reset_view()
