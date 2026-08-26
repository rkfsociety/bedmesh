"""Run the complete Windows test suite from the repository root."""

from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
TEST_DIRS = (
    ROOT / "core",
    ROOT / "utils",
    ROOT / "ui" / "components",
)


def main() -> int:
    # Keep CI/headless developer runs independent from a desktop display.
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    for path in (ROOT, ROOT / "core", ROOT / "utils", ROOT / "ui" / "components"):
        sys.path.insert(0, str(path))

    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    for test_dir in TEST_DIRS:
        suite.addTests(loader.discover(str(test_dir), pattern="test_*.py", top_level_dir=str(test_dir)))

    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
