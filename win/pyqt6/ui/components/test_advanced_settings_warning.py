import unittest
import sys
from pathlib import Path
from unittest.mock import patch

from PyQt6.QtWidgets import QApplication

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "panels"))
from left_panel import LeftPanel


class AdvancedSettingsWarningTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.panel = LeftPanel({})
        self.panel.show()
        self.app.processEvents()

    def tearDown(self):
        self.panel.deleteLater()
        self.app.processEvents()

    def test_declining_confirmation_keeps_advanced_settings_disabled(self):
        with patch.object(self.panel, "_confirm_advanced_enable", return_value=False):
            self.panel.chk_advanced.setChecked(True)
            self.panel._toggle_advanced(True)

        self.assertFalse(self.panel.chk_advanced.isChecked())
        self.assertFalse(self.panel.adv_group.isVisible())

    def test_accepting_both_confirmations_shows_advanced_settings(self):
        with patch.object(self.panel, "_confirm_advanced_enable", return_value=True):
            self.panel.chk_advanced.setChecked(True)
            self.panel._toggle_advanced(True)

        self.assertTrue(self.panel.chk_advanced.isChecked())
        self.assertTrue(self.panel.adv_group.isVisible())

    def test_enabling_advanced_settings_requires_three_warnings(self):
        with patch.object(self.panel, "_show_advanced_warning", return_value=True) as warning:
            self.assertTrue(self.panel._confirm_advanced_enable())

        self.assertEqual(warning.call_count, 3)
        self.assertTrue(all(call.args[0] == call.args[0].upper() for call in warning.call_args_list))
        self.assertTrue(all(call.args[1] == call.args[1].upper() for call in warning.call_args_list))


if __name__ == "__main__":
    unittest.main()
