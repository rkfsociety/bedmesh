import os
import sys
import unittest

import numpy as np

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from ui.components.mesh_3d_math import Z_VISUAL_SCALE, colors_from_z, scaled_z


class TestMesh3DMath(unittest.TestCase):
    def test_scaled_z_multiplies(self):
        z = np.array([[0.0, 0.1], [-0.05, 0.02]], dtype=float)
        out = scaled_z(z, scale=10.0)
        np.testing.assert_allclose(out, z * 10.0)

    def test_default_scale_constant(self):
        z = np.ones((2, 2))
        np.testing.assert_allclose(scaled_z(z), z * Z_VISUAL_SCALE)

    def test_colors_shape_and_range(self):
        z = np.linspace(-0.2, 0.3, 12).reshape(3, 4)
        c = colors_from_z(z, "soft")
        self.assertEqual(c.shape, (3, 4, 4))
        self.assertTrue(np.all(c >= 0.0) and np.all(c <= 1.0))
        # min Z → cooler end, max Z → warmer (R channel higher at max than at min for soft)
        self.assertGreater(c[2, 3, 0], c[0, 0, 0])

    def test_colors_unknown_palette_falls_back(self):
        z = np.zeros((2, 2))
        c = colors_from_z(z, "no-such-palette")
        self.assertEqual(c.shape, (2, 2, 4))


if __name__ == "__main__":
    unittest.main()
