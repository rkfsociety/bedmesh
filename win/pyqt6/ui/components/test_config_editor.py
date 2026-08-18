import os
import sys
import unittest
from pathlib import Path

from PyQt6.QtWidgets import QApplication

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
PYQT_ROOT = Path(__file__).resolve().parents[2]
if str(PYQT_ROOT) not in sys.path:
    sys.path.insert(0, str(PYQT_ROOT))

from config_editor import (  # noqa: E402
    ConfigEditor,
    KlipperConfigParser,
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
PRESETS = (100, 150, 200, 250, 300, 400, 500)


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

    def test_current_500_percent_is_selected(self):
        current = section({
            "v1_unwind_speed": "100",
            "v2_unwind_speed": "100",
            "v1_feed_speed": "150",
            "v2_feed_speed": "150",
            "unwind_speed_old_ace": "75",
            "unwind_length_after_triggered": "1220",
        })

        self.assertEqual(
            _ace_current_label(current, STANDARD, OPTIMIZED, PRESETS),
            (500, None),
        )


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


class ZHomingEditorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_advanced_editor_exposes_z_homing_controls(self):
        editor = ConfigEditor()
        editor.parser = KlipperConfigParser("")
        editor.parser.sections = {
            "stepper_z": {
                "homing_speed": ("6", 1),
                "second_homing_speed": ("3", 2),
                "homing_retract_dist": ("4", 3),
            }
        }
        editor.parser.raw_lines = [
            "[stepper_z]\n",
            "homing_speed: 6\n",
            "second_homing_speed: 3\n",
            "homing_retract_dist: 4\n",
        ]

        editor._build_ui()

        self.assertEqual(editor.widgets[("stepper_z", "homing_speed")].text(), "6")
        self.assertEqual(editor.widgets[("stepper_z", "second_homing_speed")].text(), "3")
        self.assertEqual(editor.widgets[("stepper_z", "homing_retract_dist")].text(), "4")
        editor.deleteLater()


if __name__ == "__main__":
    unittest.main()
