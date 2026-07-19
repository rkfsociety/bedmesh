import unittest
from unittest.mock import patch

from updater import _latest_release_for_platform, is_new_version


class TestPlatformReleasePick(unittest.TestCase):
    def test_picks_newest_win_not_global_latest(self):
        releases = [
            {
                "tag_name": "v0.170-android",
                "draft": False,
                "prerelease": False,
                "assets": [{"name": "BedMeshVisualizer.apk"}],
            },
            {
                "tag_name": "v0.170-mac",
                "draft": False,
                "prerelease": False,
                "assets": [{"name": "BedMeshVisualizer_Mac.dmg"}],
            },
            {
                "tag_name": "v0.170-win",
                "draft": False,
                "prerelease": False,
                "assets": [{"name": "Bed.Mesh.Visualizer.exe"}],
            },
            {
                "tag_name": "v0.169-win",
                "draft": False,
                "prerelease": False,
                "assets": [{"name": "Bed.Mesh.Visualizer.exe"}],
            },
        ]
        with patch("updater._http_get_json", return_value=releases):
            picked = _latest_release_for_platform(tag_suffix="win", asset_ext=".exe")
        self.assertIsNotNone(picked)
        self.assertEqual(picked["tag_name"], "v0.170-win")

    def test_skips_win_without_exe(self):
        releases = [
            {
                "tag_name": "v0.171-win",
                "draft": False,
                "prerelease": False,
                "assets": [{"name": "notes.txt"}],
            },
            {
                "tag_name": "v0.170-win",
                "draft": False,
                "prerelease": False,
                "assets": [{"name": "Bed.Mesh.Visualizer.exe"}],
            },
        ]
        with patch("updater._http_get_json", return_value=releases):
            picked = _latest_release_for_platform(tag_suffix="win", asset_ext=".exe")
        self.assertEqual(picked["tag_name"], "v0.170-win")

    def test_is_new_version_win_tags(self):
        self.assertTrue(is_new_version("0.169-win", "v0.170-win"))
        self.assertFalse(is_new_version("0.170-win", "v0.170-win"))


if __name__ == "__main__":
    unittest.main()
