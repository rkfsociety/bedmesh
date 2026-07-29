import os
import sys
import unittest
from unittest.mock import Mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import numpy as np
from PyQt6.QtWidgets import QApplication

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from core.mesh_parser import BedMeshData
from ui.components.mesh_3d_view import Mesh3DView


_APP = QApplication.instance() or QApplication([])


def sample_mesh():
    return BedMeshData(
        x=np.linspace(10.0, 240.0, 7),
        y=np.linspace(10.0, 240.0, 7),
        z=np.linspace(-0.1, 0.9, 49).reshape(7, 7),
        x_count=7,
        y_count=7,
        min_x=10.0,
        max_x=240.0,
        min_y=10.0,
        max_y=240.0,
    )


class TestMesh3DView(unittest.TestCase):
    def test_update_mesh_sends_flat_colors_and_fits_grid(self):
        widget = Mesh3DView()
        widget._ready = True
        widget._surface = Mock()
        widget._grid = Mock()
        widget._gl_view = Mock()
        widget._gl_view.opts = {}

        widget.update_mesh(sample_mesh())

        kwargs = widget._surface.setData.call_args.kwargs
        self.assertEqual(kwargs["z"].shape, (7, 7))
        self.assertEqual(kwargs["colors"].shape, (49, 4))
        widget._grid.setSize.assert_called_once_with(x=230.0, y=230.0)
        widget._grid.setSpacing.assert_called_once()
        widget._gl_view.set_home_view.assert_called_once()
        self.assertTrue(widget._gl_view.set_home_view.call_args.kwargs["reset"])

    def test_palette_refresh_does_not_reset_camera(self):
        widget = Mesh3DView()
        widget._ready = True
        widget._surface = Mock()
        widget._grid = Mock()
        widget._gl_view = Mock()
        widget._gl_view.opts = {}
        widget._data = sample_mesh()

        widget.set_palette("classic")

        self.assertIsNotNone(widget._gl_view.set_home_view.call_args)
        self.assertFalse(widget._gl_view.set_home_view.call_args.kwargs["reset"])


if __name__ == "__main__":
    unittest.main()
