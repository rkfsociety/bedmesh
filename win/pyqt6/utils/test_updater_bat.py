import os
import unittest

from updater import _build_replace_bat_content


class TestReplaceBatContent(unittest.TestCase):
    def test_cleans_mei_dirs_next_to_exe(self):
        base = r"C:\Users\roman\Desktop"
        content = _build_replace_bat_content(
            current_exe=os.path.join(base, "Bed.Mesh.Visualizer.exe"),
            new_exe_path=os.path.join(base, "BedMesh_Update_Temp.exe"),
            current_exe_name="Bed.Mesh.Visualizer.exe",
        )
        self.assertIn(r'for /d %%D in ("' + base + r'\_MEI*") do rd /s /q "%%~fD"', content)
        self.assertIn("LOCALAPPDATA", content)
        self.assertNotIn("--runtime-tmpdir .", content)

    def test_still_moves_update_exe(self):
        content = _build_replace_bat_content(
            current_exe=r"C:\app\Bed.Mesh.Visualizer.exe",
            new_exe_path=r"C:\app\BedMesh_Update_Temp.exe",
            current_exe_name="Bed.Mesh.Visualizer.exe",
        )
        self.assertIn(r'move /y "C:\app\BedMesh_Update_Temp.exe" "C:\app\Bed.Mesh.Visualizer.exe"', content)


if __name__ == "__main__":
    unittest.main()
