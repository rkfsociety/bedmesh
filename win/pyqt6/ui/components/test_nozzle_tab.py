import unittest

from nozzle_tab import (
    _read_nozzle_diameter,
    _read_nozzle_material,
    _replace_nozzle_diameter,
    _format_nozzle_label,
    _read_nozzle_metadata,
    _verify_remote_nozzle_values,
)


class NozzleConfigTests(unittest.TestCase):
    def test_one_millimeter_diameter_is_available(self):
        from nozzle_tab import NOZZLE_DIAMETERS

        self.assertIn("1.00", NOZZLE_DIAMETERS)

    def test_formats_material_and_diameter_for_visible_selection(self):
        self.assertEqual(_format_nozzle_label("Brass", "1.00"), "Brass-1.00")
        self.assertEqual(_format_nozzle_label("Hardened Steel", "0.40"), "Hardened Steel-0.40")

    def test_reads_material_and_diameter_from_nozzle_metadata(self):
        self.assertEqual(
            _read_nozzle_metadata('{"material":"hardened_steel","diameter":"1.00"}'),
            ("hardened_steel", "1.00"),
        )

    def test_reads_only_extruder_nozzle_diameter(self):
        text = "[heater_bed]\nnozzle_diameter: 0.80\n\n[extruder]\nnozzle_diameter : 0.400 # stock\n"

        self.assertEqual(_read_nozzle_diameter(text), "0.40")

    def test_reads_material_from_extruder(self):
        text = "[heater_bed]\nnozzle_material: brass\n\n[extruder]\nnozzle_material : hardened_steel\n"

        self.assertEqual(_read_nozzle_material(text), "hardened_steel")

    def test_replaces_value_and_preserves_other_config(self):
        text = "[extruder]\r\nrotation_distance: 6.5\r\nnozzle_diameter : 0.400 # stock\r\n\r\n[heater_bed]\r\n"

        updated = _replace_nozzle_diameter(text, "0.60")

        self.assertIn("rotation_distance: 6.5\r\n", updated)
        self.assertIn("nozzle_diameter : 0.60\r\n", updated)
        self.assertNotIn("0.400", updated)
        self.assertIn("[heater_bed]\r\n", updated)

    def test_adds_nozzle_material_when_missing(self):
        text = "[extruder]\nnozzle_diameter : 0.400\nfilament_diameter : 1.750\n"

        updated = _replace_nozzle_diameter(text, "0.40", "hardened_steel")

        self.assertIn("nozzle_material : hardened_steel\n", updated)
        self.assertLess(updated.index("nozzle_diameter"), updated.index("nozzle_material"))

    def test_rejects_config_without_extruder_diameter(self):
        with self.assertRaises(ValueError):
            _replace_nozzle_diameter("[extruder]\nrotation_distance: 6.5\n", "0.60")

    def test_verifies_both_remote_nozzle_configs_before_reboot(self):
        printer_cfg = "[extruder]\nnozzle_diameter : 1.00\nnozzle_material : hardened_steel\n"
        nozzle_cfg = '{"material":"hardened_steel","diameter":"1.00","modify":false}'

        self.assertEqual(
            _verify_remote_nozzle_values(printer_cfg, nozzle_cfg, "1.00", "hardened_steel"),
            (True, ""),
        )

    def test_rejects_nozzle_config_mismatch(self):
        printer_cfg = "[extruder]\nnozzle_diameter : 1.00\nnozzle_material : brass\n"
        nozzle_cfg = '{"material":"hardened_steel","diameter":"1.00","modify":false}'

        ok, details = _verify_remote_nozzle_values(
            printer_cfg, nozzle_cfg, "1.00", "hardened_steel"
        )
        self.assertFalse(ok)
        self.assertIn("материал", details)


if __name__ == "__main__":
    unittest.main()
