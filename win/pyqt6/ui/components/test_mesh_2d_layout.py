import os
import sys
import unittest
from pathlib import Path

import numpy as np
from PyQt6.QtWidgets import QApplication

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
PYQT_ROOT = Path(__file__).resolve().parents[2]
if str(PYQT_ROOT) not in sys.path:
    sys.path.insert(0, str(PYQT_ROOT))

from core.mesh_parser import BedMeshData  # noqa: E402
from mesh_view import MeshView  # noqa: E402
from mesh_2d_layout import (  # noqa: E402
    choose_label_font_px,
    detail_canvas_size,
    mesh_index_at_position,
)


def make_mesh(count: int) -> BedMeshData:
    x = np.linspace(0.0, 250.0, count)
    y = np.linspace(0.0, 250.0, count)
    xx, yy = np.meshgrid(x, y)
    z = 0.08 * np.sin(xx / 42.0) - 0.06 * np.cos(yy / 37.0)
    return BedMeshData(
        x=x,
        y=y,
        z=z,
        x_count=count,
        y_count=count,
        min_x=float(x.min()),
        max_x=float(x.max()),
        min_y=float(y.min()),
        max_y=float(y.max()),
    )


class Mesh2DLayoutTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_sparse_cells_keep_labels(self):
        self.assertEqual(
            choose_label_font_px(100, 100, 90, 18),
            15,
        )

    def test_dense_cells_hide_labels(self):
        self.assertIsNone(
            choose_label_font_px(700 / 31, 700 / 31, 90, 18),
        )

    def test_detail_canvas_grows_and_is_capped(self):
        self.assertEqual(detail_canvas_size(31, 31), (2976, 2976))
        self.assertEqual(detail_canvas_size(100, 100), (4096, 4096))

    def test_mouse_position_accounts_for_centering_and_y_inversion(self):
        self.assertIsNone(
            mesh_index_at_position(0, 0, 900, 700, 700, 700, 31, 31)
        )
        self.assertEqual(
            mesh_index_at_position(100, 0, 900, 700, 700, 700, 31, 31),
            (30, 0),
        )
        self.assertEqual(
            mesh_index_at_position(799, 699, 900, 700, 700, 700, 31, 31),
            (0, 30),
        )
        self.assertEqual(
            mesh_index_at_position(450, 350, 900, 700, 700, 700, 31, 31),
            (15, 15),
        )

    def test_sparse_render_uses_labels(self):
        view = MeshView()
        view.update_mesh(make_mesh(7))
        self.assertTrue(view._screen_labels_visible)

    def test_dense_render_hides_labels(self):
        view = MeshView()
        view.update_mesh(make_mesh(31))
        self.assertFalse(view._screen_labels_visible)

    def test_tooltip_returns_original_matrix_value(self):
        view = MeshView()
        mesh = make_mesh(31)
        view.resize(700, 700)
        view.show()
        self.app.processEvents()
        view.update_mesh(mesh)

        text = view.tooltip_for_position(350, 350)

        self.assertIn("Z:", text)
        self.assertIn(f"{mesh.z[15, 15]:+.3f}", text)

    def test_detail_pixmap_grows_and_keeps_labels(self):
        view = MeshView()
        view.update_mesh(make_mesh(31))

        detail = view.detail_pixmap()

        self.assertEqual((detail.width(), detail.height()), (2976, 2976))
        self.assertTrue(view._detail_labels_visible)


if __name__ == "__main__":
    unittest.main()
