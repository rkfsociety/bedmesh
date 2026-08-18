import os
import unittest

from updater import _build_powershell_start_command, _build_replace_bat_content


class TestReplaceBatContent(unittest.TestCase):
    def test_cleans_mei_dirs_next_to_exe(self):
        base = r"C:\Users\roman\Desktop"
        content = _build_replace_bat_content(
            current_exe=os.path.join(base, "Bed.Mesh.Visualizer.exe"),
            new_exe_path=os.path.join(base, "BedMesh_Update_Temp.exe"),
            current_exe_name="Bed.Mesh.Visualizer.exe",
        )
        self.assertIn(r'for /d %%D in ("' + base + r'\_MEI*") do rd /s /q "%%~fD"', content)
        self.assertIn("Windows TEMP", content)
        self.assertNotIn("--runtime-tmpdir .", content)

    def test_resets_pyinstaller_environment_before_restart(self):
        content = _build_replace_bat_content(
            current_exe=r"C:\app\Bed.Mesh.Visualizer.exe",
            new_exe_path=r"C:\app\BedMesh_Update_Temp.exe",
            current_exe_name="Bed.Mesh.Visualizer.exe",
        )
        self.assertIn('set "PYINSTALLER_RESET_ENVIRONMENT=1"', content)

    def test_still_moves_update_exe(self):
        content = _build_replace_bat_content(
            current_exe=r"C:\app\Bed.Mesh.Visualizer.exe",
            new_exe_path=r"C:\app\BedMesh_Update_Temp.exe",
            current_exe_name="Bed.Mesh.Visualizer.exe",
        )
        self.assertIn(r'move /y "C:\app\BedMesh_Update_Temp.exe" "C:\app\Bed.Mesh.Visualizer.exe"', content)

    def test_powershell_quotes_bat_path_for_cmd(self):
        command = _build_powershell_start_command(
            r"C:\Users\USSR\Desktop\updater_pyqt6.bat"
        )
        self.assertIn(
            "-ArgumentList '/d', '/c', '\"\"C:\\Users\\USSR\\Desktop\\updater_pyqt6.bat\"\"'",
            command,
        )


if __name__ == "__main__":
    unittest.main()
