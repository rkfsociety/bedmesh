import os
import sys
import unittest

import numpy as np

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from ui.components.mesh_3d_math import (
    Z_VISUAL_SCALE,
    CameraFit,
    colors_from_z,
    clamp_zoom_distance,
    fit_camera,
    prepare_surface,
    scaled_z,
    SurfacePayload,
)


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

    def test_prepare_surface_flattens_7_by_7_vertex_colors(self):
        x = np.linspace(10.0, 240.0, 7)
        y = np.linspace(10.0, 240.0, 7)
        z = np.linspace(-0.1, 0.9, 49).reshape(7, 7)

        payload = prepare_surface(x, y, z, "soft")

        self.assertIsInstance(payload, SurfacePayload)
        self.assertEqual(payload.z.shape, (7, 7))
        self.assertEqual(payload.colors.shape, (49, 4))
        self.assertEqual(payload.x.shape, (7,))
        self.assertEqual(payload.y.shape, (7,))

    def test_prepare_surface_preserves_color_order_for_rectangular_mesh(self):
        x = np.array([0.0, 10.0, 20.0])
        y = np.array([0.0, 5.0])
        z = np.array([[0.0, 0.1, 0.2], [0.3, 0.4, 0.5]])

        payload = prepare_surface(x, y, z, "soft")
        expected = np.transpose(colors_from_z(z, "soft"), (1, 0, 2)).reshape(-1, 4)

        self.assertEqual(payload.z.shape, (3, 2))
        np.testing.assert_allclose(payload.colors, expected)

    def test_prepare_surface_rejects_mismatched_shape(self):
        with self.assertRaisesRegex(ValueError, "shape"):
            prepare_surface(
                np.array([0.0, 1.0, 2.0]),
                np.array([0.0, 1.0]),
                np.zeros((3, 3)),
                "soft",
            )

    def test_fit_camera_centers_surface_and_sets_safe_limits(self):
        payload = prepare_surface(
            np.linspace(10.0, 240.0, 7),
            np.linspace(20.0, 220.0, 5),
            np.zeros((5, 7)),
            "soft",
        )

        fit = fit_camera(payload)

        self.assertIsInstance(fit, CameraFit)
        self.assertEqual(fit.center[:2], (0.0, 0.0))
        self.assertAlmostEqual(fit.center[2], payload.center_z)
        self.assertAlmostEqual(fit.distance, 230.0 * 1.8)
        self.assertLess(fit.minimum_distance, fit.distance)
        self.assertGreater(fit.maximum_distance, fit.distance)

    def test_clamp_zoom_distance_obeys_limits(self):
        self.assertEqual(clamp_zoom_distance(100.0, 100000, 20.0, 500.0), 20.0)
        self.assertEqual(clamp_zoom_distance(100.0, -100000, 20.0, 500.0), 500.0)
        self.assertLess(clamp_zoom_distance(100.0, 120, 20.0, 500.0), 100.0)
        self.assertGreater(clamp_zoom_distance(100.0, -120, 20.0, 500.0), 100.0)


if __name__ == "__main__":
    unittest.main()
