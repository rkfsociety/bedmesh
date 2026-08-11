import unittest
import hashlib
import os
import tempfile
from unittest.mock import patch

from updater import (
    _asset_digest,
    _find_checksum_asset,
    _latest_release_for_platform,
    _parse_sha256_text,
    _sha256_file,
    is_new_version,
)


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

    def test_sha256_helpers_validate_release_checksum(self):
        payload = b"bedmesh update"
        expected = hashlib.sha256(payload).hexdigest()
        with tempfile.NamedTemporaryFile(delete=False) as stream:
            stream.write(payload)
            path = stream.name
        try:
            self.assertEqual(_sha256_file(path), expected)
        finally:
            os.remove(path)

        self.assertEqual(_parse_sha256_text(f"{expected}  Bed.Mesh.Visualizer.exe"), expected)
        self.assertEqual(_asset_digest({"digest": f"sha256:{expected}"}), expected)

    def test_finds_sidecar_checksum_asset_for_exe(self):
        exe = {"name": "Bed.Mesh.Visualizer.exe"}
        checksum = {
            "name": "Bed.Mesh.Visualizer.exe.sha256",
            "browser_download_url": "https://example.invalid/checksum",
        }
        self.assertIs(_find_checksum_asset(exe, [checksum]), checksum)


if __name__ == "__main__":
    unittest.main()
