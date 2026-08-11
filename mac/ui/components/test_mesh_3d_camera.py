import os
import sys
import unittest
from unittest.mock import Mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import QPoint, QPointF, Qt
from PyQt6.QtWidgets import QApplication

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from ui.components.mesh_3d_math import CameraFit
from ui.components.mesh_3d_camera import Mesh3DGLView


_APP = QApplication.instance() or QApplication([])


class FakeMouseEvent:
    def __init__(self, position, buttons):
        self._position = QPointF(*position)
        self._buttons = buttons
        self.accepted = False

    def position(self):
        return self._position

    def buttons(self):
        return self._buttons

    def accept(self):
        self.accepted = True


class FakeWheelEvent:
    def __init__(self, delta):
        self._delta = delta
        self.accepted = False

    def angleDelta(self):
        return QPoint(0, self._delta)

    def accept(self):
        self.accepted = True


class TestMesh3DCamera(unittest.TestCase):
    def setUp(self):
        self.view = Mesh3DGLView()
        self.view.orbit = Mock()
        self.view.pan = Mock()

    def test_left_drag_orbits(self):
        self.view.mousePressEvent(FakeMouseEvent((10, 10), Qt.MouseButton.LeftButton))
        self.view.mouseMoveEvent(FakeMouseEvent((14, 16), Qt.MouseButton.LeftButton))
        self.view.orbit.assert_called_once_with(-4.0, 6.0)
        self.view.pan.assert_not_called()

    def test_right_drag_pans_in_view_plane(self):
        self.view.mousePressEvent(FakeMouseEvent((10, 10), Qt.MouseButton.RightButton))
        self.view.mouseMoveEvent(FakeMouseEvent((14, 16), Qt.MouseButton.RightButton))
        self.view.pan.assert_called_once_with(4.0, 6.0, 0, relative="view")
        self.view.orbit.assert_not_called()

    def test_wheel_zooms_within_home_limits(self):
        fit = CameraFit((0.0, 0.0, 2.0), 100.0, 20.0, 500.0)
        self.view.set_home_view(fit, reset=True)

        self.view.wheelEvent(FakeWheelEvent(120))

        self.assertLess(self.view.opts["distance"], 100.0)
        self.assertGreaterEqual(self.view.opts["distance"], 20.0)

    def test_double_click_restores_home_view(self):
        fit = CameraFit((0.0, 0.0, 2.0), 100.0, 20.0, 500.0)
        self.view.set_home_view(fit, reset=True)
        self.view.opts["distance"] = 250.0
        self.view.opts["azimuth"] = 10.0
        self.view.opts["elevation"] = 70.0
        event = FakeMouseEvent((0, 0), Qt.MouseButton.LeftButton)

        self.view.mouseDoubleClickEvent(event)

        self.assertEqual(self.view.opts["distance"], 100.0)
        self.assertEqual(self.view.opts["azimuth"], -60.0)
        self.assertEqual(self.view.opts["elevation"], 25.0)
        self.assertTrue(event.accepted)


if __name__ == "__main__":
    unittest.main()
