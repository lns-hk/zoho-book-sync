"""Start-at-login for macOS (LaunchAgent) and Windows (HKCU Run key)."""
from __future__ import annotations

import plistlib
import sys
from pathlib import Path

LABEL = "hk.lns.zohobooksync"
WIN_VALUE = "ZohoBookSync"


def _command() -> list[str]:
    if getattr(sys, "frozen", False):  # packaged app
        exe = Path(sys.executable)
        if sys.platform == "darwin" and ".app/Contents/MacOS" in str(exe):
            app = str(exe).split(".app/Contents/MacOS")[0] + ".app"
            return ["/usr/bin/open", "-g", "-a", app, "--args", "--background"]
        return [str(exe), "--background"]
    return [sys.executable, str(Path(__file__).resolve().parent.parent / "app.py"), "--background"]


def set_enabled(enabled: bool) -> None:
    if sys.platform == "darwin":
        plist = Path.home() / "Library" / "LaunchAgents" / f"{LABEL}.plist"
        if enabled:
            plist.parent.mkdir(parents=True, exist_ok=True)
            plist.write_bytes(plistlib.dumps({"Label": LABEL, "ProgramArguments": _command(), "RunAtLoad": True}))
        else:
            plist.unlink(missing_ok=True)
    elif sys.platform == "win32":
        import winreg
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run",
                             0, winreg.KEY_SET_VALUE)
        with key:
            if enabled:
                winreg.SetValueEx(key, WIN_VALUE, 0, winreg.REG_SZ, " ".join(f'"{c}"' for c in _command()))
            else:
                try:
                    winreg.DeleteValue(key, WIN_VALUE)
                except FileNotFoundError:
                    pass
