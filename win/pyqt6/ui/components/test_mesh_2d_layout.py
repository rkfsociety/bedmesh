import unittest

from mesh_2d_layout import (
    choose_label_font_px,
    detail_canvas_size,
    mesh_index_at_position,
)


class Mesh2DLayoutTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
