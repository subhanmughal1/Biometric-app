import sys
import os
from PyQt6.QtCore import Qt
from PyQt6.QtNetwork import QLocalServer, QLocalSocket
from PyQt6.QtWidgets import QApplication, QSystemTrayIcon, QMenu
from PyQt6.QtGui import QIcon
from package.views.mainwindow import MainWindow
from package.utils.logger import Logger
from package.utils.db import DbHelper
from package.config import ConfigHelper
from package.utils.paths import resource_path


icon_path = resource_path('resources', 'images', 'logo.png')


class MyApp(MainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowIcon(QIcon(icon_path))

        self.tray_icon = QSystemTrayIcon(QIcon(icon_path))
        self.tray_icon.setToolTip("BioAttendance is running. Right-click for options.")

        self.tray_menu = QMenu()
        self.tray_menu.addAction("Restore Window", self.restore_window)
        self.tray_menu.addAction("Close Program", self.exit_app)
        self.tray_icon.setContextMenu(self.tray_menu)
        self.tray_icon.activated.connect(self.tray_icon_activated)

    def show_and_activate(self, maximize: bool = False):
        self.tray_icon.hide()
        self.show()
        if self.isMinimized():
            self.showNormal()
        if maximize:
            self.showMaximized()
        else:
            self.showNormal()
        self.raise_()
        self.activateWindow()

    def minimize_to_tray(self):
        self.hide()
        self.tray_icon.show()

    def restore_window(self):
        self.show_and_activate(maximize=False)

    def tray_icon_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self.restore_window()

    def exit_app(self):
        self.tray_icon.hide()
        sys.exit(0)

    def changeEvent(self, event):
        if (event.type() == event.Type.WindowStateChange
                and self.windowState() == Qt.WindowState.WindowMinimized):
            self.minimize_to_tray()
            event.ignore()
        else:
            super().changeEvent(event)

    def closeEvent(self, event):
        self.exit_app()


def run(argv=None):
    Logger.initialize(log_file='app.log')
    try:
        if sys.platform == "win32":
            from ctypes import windll
            windll.shell32.SetCurrentProcessExplicitAppUserModelID(
                'com.mozzine.skoolzoom.bioattendance.v1'
            )
        config = ConfigHelper()
        db = DbHelper()
        db.initSchema()
        # Ensure device_type column exists (migration)
        _migrate_db(db)
    except Exception as e:
        Logger.error(f"Startup error: {e}")
        return 1

    if not os.path.exists(icon_path):
        Logger.error("Icon file not found.")
        return 1

    qt_argv = sys.argv if argv is None else argv
    app = QApplication(qt_argv)
    app.setQuitOnLastWindowClosed(False)

    server_name = "BioAttendance.SingleInstance"
    socket = QLocalSocket()
    socket.connectToServer(server_name)
    if socket.waitForConnected(150):
        try:
            socket.write(b"raise")
            socket.flush()
            socket.waitForBytesWritten(150)
        finally:
            socket.disconnectFromServer()
        return 0

    QLocalServer.removeServer(server_name)
    server = QLocalServer()
    if not server.listen(server_name):
        Logger.error(f"Single-instance server failed: {server.errorString()}")
        return 1

    window = MyApp()


    def on_new_connection():
        conn = server.nextPendingConnection()
        if conn and conn.waitForReadyRead(250):
            if bytes(conn.readAll()).strip().lower() == b"raise":
                window.show_and_activate(maximize=True)
        if conn:
            conn.disconnectFromServer()

    server.newConnection.connect(on_new_connection)
    app._single_instance_server = server
    window.show()
    Logger.info("Application started.")
    return app.exec()






def _migrate_db(db: DbHelper):
    """Add new columns to devices table if they don't exist yet."""
    try:
        db.execute_query(
            "ALTER TABLE devices ADD COLUMN device_type TEXT DEFAULT 'auto'"
        )
    except Exception:
        pass   # column already exists


if __name__ == '__main__':
    raise SystemExit(run())
