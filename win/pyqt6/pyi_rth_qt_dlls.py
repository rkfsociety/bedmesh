"""Keep PyQt6 on the Windows system ICU used by the installed Qt runtime."""

import os
import sys


if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
    # PyInstaller may copy an ICU DLL from an unrelated package in the build
    # environment.  PyQt6 itself resolves ICU from the Windows DLL path, and
    # the unrelated copy can cause WinError 127 while importing QtWidgets.
    for name in ("icuuc.dll", "icudt78.dll"):
        try:
            os.remove(os.path.join(sys._MEIPASS, name))
        except FileNotFoundError:
            pass
        except OSError:
            # The normal Qt import will provide the actionable failure if the
            # extracted runtime is unexpectedly read-only.
            pass
