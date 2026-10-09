import unittest
import json

import numpy as np

from live_mesh import LiveMeshAccumulator, update_bed_mesh_json
from mesh_parser import BedMeshData


class LiveMeshAccumulatorTests(unittest.TestCase):
    def test_repeated_probe_updates_same_cell(self):
        acc = LiveMeshAccumulator(total_points=4)
        self.assertTrue(acc.feed_line("[Probe] probe at 10.000,20.000 is z=0.100000"))
        self.assertTrue(acc.feed_line("[Probe] probe at 10.000,20.000 is z=0.125000"))
        snapshot = acc.snapshot()
        self.assertIsNotNone(snapshot)
        self.assertEqual(snapshot.measured_points, 1)
        self.assertEqual(snapshot.total_points, 4)
        self.assertEqual(snapshot.current, (10.0, 20.0))
        np.testing.assert_allclose(snapshot.data.z, [[0.125]])

    def test_partial_grid_fills_unknown_cells_with_known_mean(self):
        acc = LiveMeshAccumulator()
        acc.feed_line("probe at 0,0 is z=-0.2")
        acc.feed_line("probe at 10,0 is z=0.2")
        snapshot = acc.snapshot()
        self.assertEqual(snapshot.measured_points, 2)
        np.testing.assert_allclose(snapshot.data.z, [[-0.2, 0.2]])

    def test_ignores_unrelated_lines(self):
        acc = LiveMeshAccumulator()
        self.assertFalse(acc.feed_line("Move Z to 3"))
        self.assertIsNone(acc.snapshot())

    def test_fixed_grid_preserves_physical_orientation_for_snake_order(self):
        acc = LiveMeshAccumulator(
            total_points=4,
            x=np.array([0.0, 10.0]),
            y=np.array([0.0, 10.0]),
        )
        # Firmware order: bottom row left-to-right, next row right-to-left.
        for line in (
            "probe at 0,0 is z=1.0",
            "probe at 10,0 is z=2.0",
            "probe at 10,10 is z=3.0",
            "probe at 0,10 is z=4.0",
        ):
            acc.feed_line(line)
        snapshot = acc.snapshot()
        np.testing.assert_allclose(snapshot.data.z, [[1.0, 2.0], [4.0, 3.0]])

    def test_update_bed_mesh_json_replaces_points_and_grid(self):
        data = BedMeshData(
            x=np.array([0.0, 250.0]),
            y=np.array([0.0, 250.0]),
            z=np.array([[1.25, -0.5], [0.125, 2.0]]),
            x_count=2,
            y_count=2,
            min_x=0.0,
            max_x=250.0,
            min_y=0.0,
            max_y=250.0,
        )
        result = json.loads(
            update_bed_mesh_json(
                json.dumps({"bed_mesh default": {"algo": "bicubic"}, "other": {"v": 1}}),
                data,
            )
        )
        mesh = result["bed_mesh default"]
        self.assertEqual(mesh["x_count"], "2")
        self.assertEqual(mesh["y_count"], "2")
        self.assertEqual(mesh["points"], "1.250000, -0.500000\n0.125000, 2.000000")
        self.assertEqual(result["other"], {"v": 1})

    def test_update_bed_mesh_json_rejects_invalid_shape(self):
        data = BedMeshData(
            x=np.array([0.0]), y=np.array([0.0]), z=np.array([[1.0]]),
            x_count=2, y_count=2, min_x=0.0, max_x=1.0, min_y=0.0, max_y=1.0,
        )
        with self.assertRaises(ValueError):
            update_bed_mesh_json('{"bed_mesh default": {}}', data)


if __name__ == "__main__":
    unittest.main()
