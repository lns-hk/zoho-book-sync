"""Zoho Book Sync — entry point."""
import logging
import logging.handlers
import sys

from PySide6.QtNetwork import QLocalServer, QLocalSocket
from PySide6.QtWidgets import QApplication

from zoho_sync.config import LOG_DIR, Settings
from zoho_sync.gui import MainWindow, apply_language, make_icon

INSTANCE_KEY = "ZohoBookSync-single-instance"


def setup_logging():
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    h = logging.handlers.RotatingFileHandler(LOG_DIR / "zoho_book_sync.log", maxBytes=1_000_000,
                                             backupCount=3, encoding="utf-8")
    h.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logging.basicConfig(level=logging.INFO, handlers=[h, logging.StreamHandler()])


def main():
    setup_logging()
    app = QApplication(sys.argv)
    app.setApplicationName("Zoho Book Sync")
    app.setWindowIcon(make_icon())
    app.setQuitOnLastWindowClosed(False)  # keep running in the tray

    # second launch: tell the running copy to show itself, then exit
    sock = QLocalSocket()
    sock.connectToServer(INSTANCE_KEY)
    if sock.waitForConnected(300):
        if sys.platform == "win32":  # let the running copy take the foreground (Windows focus-steal lock)
            import ctypes
            ctypes.windll.user32.AllowSetForegroundWindow(-1)  # ASFW_ANY
        sock.write(b"show"); sock.flush(); sock.waitForBytesWritten(300)
        return 0
    QLocalServer.removeServer(INSTANCE_KEY)
    server = QLocalServer()
    server.listen(INSTANCE_KEY)

    apply_language(Settings.load().language)  # before any window is built
    win = MainWindow(start_hidden="--background" in sys.argv)
    server.newConnection.connect(lambda: (server.nextPendingConnection(), win.show_window()))
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
