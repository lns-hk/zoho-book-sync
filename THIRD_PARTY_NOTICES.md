# Third-party notices

Zoho Book Sync is licensed under the MIT License (see [`LICENSE`](LICENSE)).
The packaged macOS and Windows releases also bundle the following third-party software, each under its own license.

## Qt for Python (PySide6, Shiboken6) and Qt 6

- Copyright (C) The Qt Company Ltd. and other contributors
- License: GNU Lesser General Public License v3.0 (LGPL-3.0); the full texts are in [`licenses/LGPL-3.0.txt`](licenses/LGPL-3.0.txt) and [`licenses/GPL-3.0.txt`](licenses/GPL-3.0.txt), which the LGPL incorporates.
- Source code: https://code.qt.io/ (PySide6: https://code.qt.io/cgit/pyside/pyside-setup.git/) and https://pypi.org/project/PySide6/
- Version used: 6.12.0, unmodified.

Zoho Book Sync uses these libraries without modifying them. They are included as separate shared libraries in the packaged app (`ZohoBookSync.app/Contents/Frameworks` and `Contents/Resources/PySide6` on macOS, `ZohoBookSync\_internal\PySide6` on Windows), so you can replace them with your own compatible build. You can also run the app from source with any compatible PySide6 version; see the README.

## platformdirs

- Copyright (c) 2010-202x platformdirs developers
- License: MIT — https://github.com/tox-dev/platformdirs/blob/main/LICENSE

## Python

- Copyright (c) 2001 Python Software Foundation; All Rights Reserved
- License: Python Software Foundation License Version 2 — https://docs.python.org/3/license.html

## PyInstaller bootloader

- Copyright (c) 2010-2026, PyInstaller Development Team
- License: GPL-2.0 with a special exception that allows the bootloader to be used in programs under any license — https://github.com/pyinstaller/pyinstaller/blob/develop/COPYING.txt

## Zoho

Zoho and Zoho Books are trademarks of Zoho Corporation. Zoho Book Sync is an independent project and is not made, endorsed or supported by Zoho Corporation.
