import os
import sys
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
PYQT_ROOT = Path(__file__).resolve().parents[2]
if str(PYQT_ROOT) not in sys.path:
    sys.path.insert(0, str(PYQT_ROOT))

from config_editor import (  # noqa: E402
    _ace_current_label,
    _ace_preset_matches,
    _parse_probe_count,
    _probe_count_allows_lagrange,
)


STANDARD = {
    "v1_unwind_speed": "20",
    "v2_unwind_speed": "20",
    "v1_feed_speed": "30",
    "v2_feed_speed": "30",
    "unwind_speed_old_ace": "15",
    "unwind_length_after_triggered": "1300",
}
OPTIMIZED = {"unwind_length_after_triggered": "1220"}
PRESETS = (100, 150, 200, 250, 300)


def section(values: dict[str, str]) -> dict[str, tuple[str, int]]:
    return {key: (value, 0) for key, value in values.items()}


class AcePresetTests(unittest.TestCase):
    def test_current_300_percent_is_selected(self):
        current = section({
            "v1_unwind_speed": "60",
            "v2_unwind_speed": "60",
            "v1_feed_speed": "90",
            "v2_feed_speed": "90",
            "unwind_speed_old_ace": "45",
            "unwind_length_after_triggered": "1220",
        })

        self.assertTrue(_ace_preset_matches(current, 300, STANDARD, OPTIMIZED))
        self.assertEqual(
            _ace_current_label(current, STANDARD, OPTIMIZED, PRESETS),
            (300, None),
        )

    def test_non_preset_values_are_shown_as_current(self):
        current = section({
            "v1_unwind_speed": "21",
            "v2_unwind_speed": "21",
            "v1_feed_speed": "31",
            "v2_feed_speed": "31",
            "unwind_speed_old_ace": "16",
            "unwind_length_after_triggered": "1220",
        })

        percent, label = _ace_current_label(current, STANDARD, OPTIMIZED, PRESETS)

        self.assertIsNone(percent)
        self.assertEqual(label, "Текущее: ~105%")


class ProbeCountTests(unittest.TestCase):
    def test_single_value_is_used_for_both_axes(self):
        self.assertEqual(_parse_probe_count("5"), (5, 5))

    def test_lagrange_allowed_only_up_to_five_points_per_axis(self):
        self.assertTrue(_probe_count_allows_lagrange("5,5"))
        self.assertTrue(_probe_count_allows_lagrange("3,5"))
        self.assertFalse(_probe_count_allows_lagrange("6,5"))
        self.assertFalse(_probe_count_allows_lagrange("10"))

    def test_incomplete_value_does_not_lock_the_editor(self):
        self.assertIsNone(_parse_probe_count("5,"))
        self.assertTrue(_probe_count_allows_lagrange("5,"))


if __name__ == "__main__":
    unittest.main()
