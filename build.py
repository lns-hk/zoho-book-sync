"""Build the desktop app with PyInstaller.  Run on each OS:  python build.py
macOS  -> dist-mac/ZohoBookSync.app  (+ dist-mac/ZohoBookSync-mac.zip)
Windows-> dist-windows/ZohoBookSync/ZohoBookSync.exe (+ dist-windows/ZohoBookSync-windows.zip)
"""
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from zoho_sync import __version__

ROOT = Path(__file__).resolve().parent
subprocess.check_call([sys.executable, "make_icon.py"], cwd=ROOT)

args = [
    sys.executable, "-m", "PyInstaller", "app.py", "--noconfirm", "--clean", "--windowed",
    "--name", "ZohoBookSync", "--icon", "assets/icon.png",
    "--workpath", str(Path(tempfile.gettempdir()) / "zohobooksync-build"),  # keep scratch out of synced folders
    "--distpath", "dist-mac" if sys.platform == "darwin" else "dist-windows",
    "--exclude-module", "tkinter",
    # trim unused Qt modules to keep the bundle small
    *[a for m in ("QtWebEngineCore", "QtWebEngineWidgets", "QtQml", "QtQuick", "Qt3DCore", "QtMultimedia",
                  "QtPdf", "QtCharts", "QtDataVisualization", "QtSql", "QtTest")
      for a in ("--exclude-module", f"PySide6.{m}")],
]
if sys.platform == "darwin":
    args += ["--osx-bundle-identifier", "hk.lns.zohobooksync"]
subprocess.check_call(args, cwd=ROOT)

dist = ROOT / ("dist-mac" if sys.platform == "darwin" else "dist-windows")
if sys.platform == "darwin":
    plist = dist / "ZohoBookSync.app" / "Contents" / "Info.plist"
    import plistlib
    info = plistlib.loads(plist.read_bytes())
    info.update({"CFBundleDisplayName": "Zoho Book Sync", "CFBundleShortVersionString": __version__,
                 "CFBundleVersion": __version__, "NSHighResolutionCapable": True})
    plist.write_bytes(plistlib.dumps(info))
    subprocess.check_call(["codesign", "--force", "--deep", "--sign", "-", str(dist / "ZohoBookSync.app")])
    subprocess.check_call(["ditto", "-c", "-k", "--keepParent", "ZohoBookSync.app", "ZohoBookSync-mac.zip"], cwd=dist)
    print("built", dist / "ZohoBookSync-mac.zip")
else:
    shutil.make_archive(str(dist / "ZohoBookSync-windows"), "zip", dist, "ZohoBookSync")
    print("built", dist / "ZohoBookSync-windows.zip")
