import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

PYQT_ROOT = Path(__file__).resolve().parents[1]
if str(PYQT_ROOT) not in sys.path:
    sys.path.insert(0, str(PYQT_ROOT))

from mesh_parser import MeshParser  # noqa: E402


CONFIG_TEXT = """
[bed_mesh default]
version = 1
points =
      0.012, 0.005, -0.008
      0.010, 0.003, -0.006
      0.008, 0.001, -0.004
x_count = 3
y_count = 3
min_x = 20.0
max_x = 280.0
min_y = 20.0
max_y = 280.0

[input_shaper]
shaper_type_x = mzv
shaper_freq_x = 40.0
shaper_type_y = ei
shaper_freq_y = 35.0
"""


class MeshParserTests(unittest.TestCase):
    def setUp(self):
        self.parser = MeshParser()

    def test_parse_klipper_config_matrix_and_shaper(self):
        data = self.parser.parse_text(CONFIG_TEXT)

        self.assertIsNotNone(data)
        self.assertEqual((data.x_count, data.y_count), (3, 3))
        np.testing.assert_allclose(
            data.z,
            np.array([
                [0.012, 0.005, -0.008],
                [0.010, 0.003, -0.006],
                [0.008, 0.001, -0.004],
            ]),
        )
        self.assertEqual(data.min_x, 20.0)
        self.assertEqual(data.max_y, 280.0)
        self.assertEqual(
            self.parser.parse_input_shaper_text(CONFIG_TEXT),
            {
                "shaper_type_x": "mzv",
                "shaper_type_y": "ei",
                "shaper_freq_x": 40.0,
                "shaper_freq_y": 35.0,
            },
        )

    def test_parse_json_mesh_and_json_shaper(self):
        payload = {
            "bed_mesh default": {
                "x_count": 2,
                "y_count": 2,
                "min_x": 0,
                "max_x": 10,
                "min_y": 1,
                "max_y": 11,
                "points": "0.1, 0.2, 0.3, 0.4",
            },
            "input_shaper": {
                "shaper_type_x": "ZV",
                "shaper_type_y": "MZV",
                "shaper_freq_x": "50",
                "shaper_freq_y": 55,
            },
        }

        data = self.parser.parse_text(json.dumps(payload))

        self.assertEqual((data.x_count, data.y_count), (2, 2))
        np.testing.assert_allclose(data.z, [[0.1, 0.2], [0.3, 0.4]])
        self.assertEqual(
            self.parser.parse_input_shaper_text(json.dumps(payload)),
            {
                "shaper_type_x": "zv",
                "shaper_type_y": "mzv",
                "shaper_freq_x": 50.0,
                "shaper_freq_y": 55.0,
            },
        )

    def test_parse_file_uses_utf8_and_matches_parse_text(self):
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", suffix=".cfg", delete=False
        ) as file:
            file.write(CONFIG_TEXT)
            path = file.name
        try:
            from_file = self.parser.parse_file(path)
            from_text = self.parser.parse_text(CONFIG_TEXT)
            np.testing.assert_allclose(from_file.z, from_text.z)
        finally:
            os.remove(path)

    def test_invalid_or_incomplete_mesh_returns_none(self):
        self.assertIsNone(self.parser.parse_text("[bed_mesh]\nx_count: 0\n"))
        self.assertIsNone(self.parser.parse_input_shaper_text(
            "[input_shaper]\nshaper_freq_x: 0\nshaper_freq_y: 40\n"
        ))

    def test_parse_print_size(self):
        self.assertEqual(
            self.parser.parse_print_size("[printer]\nprint_size: 250*250*250mm\n"),
            (250.0, 250.0),
        )

    def test_parse_config_attaches_printable_area(self):
        text = CONFIG_TEXT.replace(
            "[bed_mesh default]",
            "[printer]\nprint_size: 250*250*250mm\n\n[bed_mesh default]",
        )
        data = self.parser.parse_text(text)
        self.assertEqual((data.bed_min_x, data.bed_max_x), (0.0, 250.0))
        self.assertEqual((data.bed_min_y, data.bed_max_y), (0.0, 250.0))


if __name__ == "__main__":
    unittest.main()
