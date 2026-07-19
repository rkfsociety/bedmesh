import os
import tempfile
import unittest
from unittest.mock import patch

from app_config import default_download_local_path, get_cache_dir


class TestCachePaths(unittest.TestCase):
    def test_default_download_uses_cache_subdir(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch("app_config.get_app_data_dir", return_value=tmp):
                path = default_download_local_path("/userdata/app/gk/printer.cfg")
                self.assertEqual(path, os.path.join(tmp, "cache", "download_printer.cfg"))
                self.assertTrue(os.path.isdir(os.path.join(tmp, "cache")))

    def test_default_download_mutable_name(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch("app_config.get_app_data_dir", return_value=tmp):
                path = default_download_local_path("/userdata/app/gk/printer_mutable.cfg")
                self.assertEqual(
                    path,
                    os.path.join(tmp, "cache", "download_printer_mutable.cfg"),
                )

    def test_get_cache_dir_creates_cache(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch("app_config.get_app_data_dir", return_value=tmp):
                cache = get_cache_dir()
                self.assertEqual(cache, os.path.join(tmp, "cache"))
                self.assertTrue(os.path.isdir(cache))


if __name__ == "__main__":
    unittest.main()
