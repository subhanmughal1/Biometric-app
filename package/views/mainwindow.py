"""
MainWindow  ─  View Layer (MVC)
================================
View responsibilities:
  - Display data given by Controller
  - Forward user actions to Controller
  - NEVER talk to ZK SDK, database, or HTTP directly

All business logic has moved to DeviceController.
"""

import os
from datetime import datetime
from PyQt6 import uic, QtCore
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QMenu, QGroupBox, QTabWidget,
    QLineEdit, QDialog, QTableView, QHeaderView, QPushButton, QComboBox
)
from PyQt6.QtGui import QPixmap, QStandardItemModel, QStandardItem, QCursor, QIcon

from package.controllers.device_controller import DeviceController
from package.threads.network_manager import ConnectionManager
from package.threads.data_manager import DataCleaningManager, DataSyncManager
from package.threads.attendance_manager import (
    AttendanceCleaningManager, AttendancePostingManager, LiveAttendanceManager
)
from package.threads.network_thread import NetworkThread
from package.utils.api import APIHelper
from package.utils.logger import Logger
from package.utils.helper import Alert
from package.utils.dialogs import CustomIPDialog
from package.config import ConfigHelper
from package.utils.paths import resource_path
from pathlib import Path


class MainWindow(QMainWindow):
    """
    Pure View. Uses DeviceController for all business logic.
    """

    def __init__(self):
        super().__init__()
        self.ui = uic.loadUi(
            os.path.join(Path(__file__).parent.parent.resolve(), "ui", "src", "mainwindow.ui"), self
        )

        # ── MVC: Controller ──────────────────────────────────────────
        self._controller = DeviceController()

        # ── Legacy attributes (kept for thread compatibility) ─────────
        self.thread = {}
        self.data = {}
        self.clients = {}                         # ip → ZkClient (threads read this)
        self.selectedUser = {}
        self.selectedDevice = {"ipaddress": None, "client": None}
        self.appConfig = ConfigHelper()

        # ── Window setup ─────────────────────────────────────────────
        self.setWindowFlags(
            QtCore.Qt.WindowType.CustomizeWindowHint
            | QtCore.Qt.WindowType.WindowCloseButtonHint
            | QtCore.Qt.WindowType.WindowMinimizeButtonHint
            | QtCore.Qt.WindowType.WindowMaximizeButtonHint
        )
        self.setWindowTitle(self.appConfig.appName)
        self.schoolName.setText(self.appConfig.read_config("schoolName"))

        # ── Thread managers (use self.clients — populated by controller) ─
        self.dataSyncManager         = DataSyncManager(ref=self)
        self.connectionManager       = ConnectionManager(ref=self)
        self.dataCleaningManager     = DataCleaningManager(ref=self)
        self.liveAttendanceManager   = LiveAttendanceManager(ref=self)
        self.attendancePostingManager = AttendancePostingManager(ref=self)
        self.attendanceCleaningManager = AttendanceCleaningManager(ref=self)

        # ── Icons ────────────────────────────────────────────────────
        self._setup_icons()

        # ── Tab widget ───────────────────────────────────────────────
        self.tabWidget = self.findChild(QTabWidget, "windowTabs")
        self.tabWidget.currentChanged.connect(self.on_tab_changed)

        # ── Devices tab setup ────────────────────────────────────────
        self._setup_devices_tab()

        # ── Users tab setup ──────────────────────────────────────────
        self._setup_users_tab()

        # ── Settings tab ─────────────────────────────────────────────
        self.apiKey.setText(str(self.appConfig.read_config("apiKey")))
        self.schoolURL.setText(str(self.appConfig.read_config("schoolURL")))
        self.buttonDownloadConfig.clicked.connect(self.on_download_config_click)

        # ── About tab ────────────────────────────────────────────────
        self.companyNameLabelValue.setText(str(self.appConfig.read_config("providerName")))
        self.websiteLabelValue.setText(str(self.appConfig.read_config("providerWebsite")))

        # ── Boot ─────────────────────────────────────────────────────
        self.isCheckinMode = True
        self.setConnectionText("waiting for the connection...")
        self.show()
        QtCore.QTimer.singleShot(100, self.boot_after_ui)

    # ── Setup helpers ────────────────────────────────────────────────

    def _setup_icons(self):
        R = resource_path
        self.windowTabs.setTabIcon(0, QIcon(R("resources", "icons", "connect.png")))
        self.windowTabs.setTabIcon(1, QIcon(R("resources", "icons", "machine.png")))
        self.windowTabs.setTabIcon(2, QIcon(R("resources", "icons", "users.png")))
        self.windowTabs.setTabIcon(3, QIcon(R("resources", "icons", "settings.png")))
        self.windowTabs.setTabIcon(4, QIcon(R("resources", "icons", "information-italic.png")))
        self.buttonDownloadConfig.setIcon(QIcon(R("resources", "icons", "check.png")))
        self.buttonRestartDevice.setIcon(QIcon(R("resources", "icons", "play.png")))
        self.buttonCleanAttendance.setIcon(QIcon(R("resources", "icons", "eraser-minus.png")))
        self.buttonSyncAll.setIcon(QIcon(R("resources", "icons", "download.png")))
        self.buttonCleanData.setIcon(QIcon(R("resources", "icons", "cancel.png")))
        self.buttonSyncStudents.setIcon(QIcon(R("resources", "icons", "students.png")))
        self.buttonSyncStaff.setIcon(QIcon(R("resources", "icons", "staff.png")))
        self.scanNetworkButton.setIcon(QIcon(R("resources", "icons", "refresh.png")))
        self.addIPButton.setIcon(QIcon(R("resources", "icons", "plus.png")))

    def _setup_devices_tab(self):
        self.boxNetworkDevices         = self.findChild(QGroupBox, "boxNetworkDevices")
        self.scanNetworkButton         = self.findChild(QPushButton, "scanNetworkButton")
        self.devicesTableView          = self.findChild(QTableView, "devicesTableView")
        self.networkDevicesTableView   = self.findChild(QTableView, "networkDevicesTableView")

        self.devicesModel = QStandardItemModel()
        self.networkDevicesModel = QStandardItemModel()
        self.devicesModel.setHorizontalHeaderLabels(["Device Name", "IP Address", "Vendor", "Port"])
        self.networkDevicesModel.setHorizontalHeaderLabels(["IP Address", "Type", "Action"])

        self.devicesTableView.setModel(self.devicesModel)
        self.devicesTableView.setSelectionMode(QTableView.SelectionMode.SingleSelection)
        self.devicesTableView.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self.devicesTableView.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        self.devicesTableView.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

        self.networkDevicesTableView.setModel(self.networkDevicesModel)
        self.networkDevicesTableView.setSelectionMode(QTableView.SelectionMode.SingleSelection)
        self.networkDevicesTableView.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self.networkDevicesTableView.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        self.networkDevicesTableView.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

        self.buttonRestartDevice.clicked.connect(self.on_restart_device_click)
        self.buttonCleanAttendance.clicked.connect(self.on_clean_attendance_click)
        self.buttonCleanData.clicked.connect(self.on_clean_data_click)
        self.buttonSyncAll.clicked.connect(self.on_sync_all_click)
        self.buttonSyncStaff.clicked.connect(self.on_sync_staff_click)
        self.buttonSyncStudents.clicked.connect(self.on_sync_students_click)
        self.addIPButton.clicked.connect(self.on_add_ip_click)
        self.scanNetworkButton.clicked.connect(self.on_start_network_scan_click)
        self.devicesTableView.clicked.connect(self.select_device_from_table)
        self.devicesTableView.customContextMenuRequested.connect(self.show_devices_table_context_menu)
        self.networkDevicesTableView.customContextMenuRequested.connect(
            self.show_network_devices_table_context_menu
        )

    def _setup_users_tab(self):
        self.usersTableView   = self.findChild(QTableView, "usersTableView")
        self.usersTableSearch = self.findChild(QLineEdit, "usersTableSearch")
        self.usersModel = QStandardItemModel()
        self.usersModel.setHorizontalHeaderLabels(
            ["UID", "User Name", "Check In", "Check Out", "OT In", "OT Out"]
        )
        self.usersTableView.setModel(self.usersModel)
        self.usersTableView.setSelectionMode(QTableView.SelectionMode.SingleSelection)
        self.usersTableView.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self.usersTableView.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        self.usersTableView.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.usersTableView.clicked.connect(self.select_user_from_table)
        self.usersTableView.customContextMenuRequested.connect(self.show_users_table_context_menu)

        self.devicesDropdown = self.findChild(QComboBox, "clientsDropdown")
        self.devicesDropdown.addItem("Select a device")
        self.devicesDropdown.currentIndexChanged.connect(self.on_dropdown_device_selected)
        self.usersTableSearch.textChanged.connect(self.filter_users_table)

    # ── Boot ──────────────────────────────────────────────────────────

    def boot_after_ui(self):
        self.loadSavedDevices()
        self.update_biometric_status()
        self.connectionManager.start()
        self.attendancePostingManager.start()
        self.liveAttendanceManager.start()

    # ── Tab handler ───────────────────────────────────────────────────

    def on_tab_changed(self, index):
        pass   # extend as needed

    # ── Connection tab ────────────────────────────────────────────────

    def setConnectionText(self, text: str):
        self.connectionStatus.setText(text)

    # ── Device tab: actions ───────────────────────────────────────────

    def on_restart_device_click(self):
        ip = self.selectedDevice.get("ipaddress")
        if not ip:
            self.postDeviceLog("", "Select a device first", "red")
            return
        if self._controller.restart_device(ip):
            self.postDeviceLog(ip, "Restart request sent to device", "blue")
        else:
            self.postDeviceLog(ip, "Device not responding", "red")

    def on_clean_attendance_click(self):
        ip = self.selectedDevice.get("ipaddress")
        if ip:
            self.postDeviceLog(ip, "Log Cleaning process started...", "blue")
            self.attendanceCleaningManager.start(ip)
        else:
            self.postDeviceLog("", "Select a device first", "red")

    def on_clean_data_click(self):
        ip = self.selectedDevice.get("ipaddress")
        if ip:
            self.postDeviceLog(ip, "Cleaning process started...", "blue")
            self.dataCleaningManager.start(ip)
        else:
            self.postDeviceLog("", "Select a device first", "red")

    def on_sync_all_click(self):
        ip = self.selectedDevice.get("ipaddress")
        if ip:
            self.postDeviceLog(ip, "Users sync process started...", "blue")
            self.dataSyncManager.start(ip)
        else:
            self.postDeviceLog("", "Select a device first", "red")

    def on_sync_staff_click(self):
        ip = self.selectedDevice.get("ipaddress")
        if ip:
            self.postDeviceLog(ip, "Staff sync process started...", "blue")
            self.dataSyncManager.start(ip, type="staff")
        else:
            self.postDeviceLog("", "Select a device first", "red")

    def on_sync_students_click(self):
        ip = self.selectedDevice.get("ipaddress")
        if ip:
            self.postDeviceLog(ip, "Student sync process started...", "blue")
            self.dataSyncManager.start(ip, type="students")
        else:
            self.postDeviceLog("", "Select a device first", "red")

    def on_add_ip_click(self):
        dialog = CustomIPDialog()
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.loadSavedDevices()

    def on_start_network_scan_click(self):
        self.startNetworkTread()

    def select_network_device(self, row: int):
        col_count = self.networkDevicesModel.columnCount()
        row_data = [self.networkDevicesModel.item(row, c).text() for c in range(col_count)]
        ip = row_data[0]
        vendor = row_data[1]
        self._controller.add_device(ip, vendor=vendor)

    def show_network_devices_table_context_menu(self, position: QtCore.QPoint):
        index = self.networkDevicesTableView.indexAt(position)
        if not index.isValid():
            return
        menu = QMenu(self)
        action = menu.addAction("Select Device")
        selected = menu.exec(self.networkDevicesTableView.viewport().mapToGlobal(position))
        if selected == action:
            self.select_network_device(index.row())
            self.loadSavedDevices()

    def remove_device(self, row: int):
        col_count = self.devicesModel.columnCount()
        row_data = [
            (self.devicesModel.item(row, c).text() if self.devicesModel.item(row, c) else "")
            for c in range(col_count)
        ]
        ip = row_data[1] if len(row_data) > 1 else ""
        if ip:
            self._controller.remove_device(ip)
            self.loadSavedDevices()

    def show_devices_table_context_menu(self, position: QtCore.QPoint):
        index = self.devicesTableView.indexAt(position)
        if not index.isValid():
            return
        menu = QMenu(self)
        action = menu.addAction("Remove Device")
        selected = menu.exec(self.devicesTableView.viewport().mapToGlobal(position))
        if selected == action:
            self.remove_device(index.row())

    def select_device_from_table(self):
        indexes = self.devicesTableView.selectionModel().selectedRows()
        if not indexes:
            return
        row = indexes[0].row()
        row_data = [
            self.devicesModel.data(self.devicesModel.index(row, c))
            for c in range(self.devicesModel.columnCount())
        ]
        ip = row_data[1]
        self.selectedDevice["ipaddress"] = ip
        self.selectedDevice["vendor"]    = row_data[2]
        self.selectedDevice["client"]    = self.clients.get(ip)
        self.updateDeviceOptions()

    def postDeviceLog(self, ip: str = "", text: str = "", color: str = ""):
        prefix = f"{ip}: " if ip else ""
        if color:
            if prefix:
                self.textBrowserSelectedDeviceLog.append(
                    f'<span style="color:{color};">{prefix}</span>'
                )
            self.textBrowserSelectedDeviceLog.append(
                f'<span style="color:{color};">{text}</span>'
            )
        else:
            if prefix:
                self.textBrowserSelectedDeviceLog.append(prefix)
            self.textBrowserSelectedDeviceLog.append(str(text))

    def updateDeviceOptions(self):
        """Fetch device info via controller and populate UI labels."""
        ip = self.selectedDevice.get("ipaddress")
        if not ip:
            return
        info = self._controller.get_device_info(ip)
        if not info:
            self.postDeviceLog(ip, "Device not responding", "red")
            return
        try:
            self.deviceNameLabelValue.setText(info["device_name"])
            self.devicePlatformLabelValue.setText(info["platform"])
            self.deviceSerialNumberLabelValue.setText(info["serial_number"])
            self.deviceFirmwareVersionLabelValue.setText(info["firmware_version"])
            self.deviceGatewayLabelValue.setText(info["gateway"])
            self.deviceMACAddressLabelValue.setText(info["mac_address"])
            self.deviceTimeLabelValue.setText(info["time"])
        except Exception as e:
            Logger.error(f"[MainWindow] updateDeviceOptions {ip}: {e}")

    def loadSavedDevices(self):
        """Reload device list from controller → update UI tables + threads."""
        self.devicesModel.removeRows(0, self.devicesModel.rowCount())
        self.devicesDropdown.clear()
        self.devicesDropdown.addItem("Select a device")

        # Tell controller to rebuild client pool
        self.clients = self._controller.build_clients()

        devices = self._controller.get_all_devices()
        for d in devices:
            ip = str(d["ipaddress"])
            self.devicesDropdown.addItem(ip)
            row = [
                QStandardItem(str(d.get("name", ""))),
                QStandardItem(ip),
                QStandardItem(str(d.get("vendor", "ZKTeco"))),
                QStandardItem(str(d.get("port", 4370))),
            ]
            self.devicesModel.appendRow(row)

    # ── Users tab ──────────────────────────────────────────────────────

    def show_users_table_context_menu(self, position: QtCore.QPoint):
        index = self.usersTableView.indexAt(position)
        if not index.isValid():
            return
        menu = QMenu(self)
        action = menu.addAction("Delete User")
        selected = menu.exec(self.usersTableView.viewport().mapToGlobal(position))
        if selected == action:
            ip = self.selectedDevice.get("ipaddress")
            uid = self.selectedUser.get("uid")
            if ip and uid:
                self._controller.delete_device_user(ip, int(uid))
                self.loadDeviceUsers()

    def select_user_from_table(self):
        try:
            indexes = self.usersTableView.selectionModel().selectedRows()
            if indexes:
                row = indexes[0].row()
                row_data = [
                    self.usersModel.data(self.usersModel.index(row, c))
                    for c in range(self.usersModel.columnCount())
                ]
                self.selectedUser["uid"]  = row_data[0]
                self.selectedUser["name"] = row_data[1]
        except Exception as e:
            Logger.error(f"[MainWindow] select_user_from_table: {e}")

    def loadDeviceUsers(self):
        """Fetch users + today's attendance via controller → populate table."""
        try:
            self.usersModel.removeRows(0, self.usersModel.rowCount())
            ip = self.selectedDevice.get("ipaddress")
            if not ip:
                return

            users = self._controller.get_device_users(ip)
            attendance = self._controller.get_date_attendance(ip)

            for user in users:
                checkin_time = checkout_time = ot_in = ot_out = "-"
                try:
                    uid = int(user.uid)
                    ci = [a for a in attendance if int(a.user_id) == uid and a.punch == 0]
                    co = [a for a in attendance if int(a.user_id) == uid and a.punch == 1]
                    oi = [a for a in attendance if int(a.user_id) == uid and a.punch == 4]
                    oo = [a for a in attendance if int(a.user_id) == uid and a.punch == 5]
                    if ci: checkin_time  = ci[0].timestamp.strftime("%I:%M %p")
                    if co: checkout_time = co[0].timestamp.strftime("%I:%M %p")
                    if oi: ot_in         = oi[0].timestamp.strftime("%I:%M %p")
                    if oo: ot_out        = oo[0].timestamp.strftime("%I:%M %p")
                except Exception as e:
                    Logger.error(f"[MainWindow] loadDeviceUsers time calc: {e}")

                self.usersModel.appendRow([
                    QStandardItem(str(user.uid)),
                    QStandardItem(str(user.name)),
                    QStandardItem(checkin_time),
                    QStandardItem(checkout_time),
                    QStandardItem(ot_in),
                    QStandardItem(ot_out),
                ])
        except Exception as e:
            Logger.error(f"[MainWindow] loadDeviceUsers: {e}")

    def on_dropdown_device_selected(self, index: int):
        try:
            self.selectedDevice = {"ipaddress": None, "client": None}
            ip = self.devicesDropdown.itemText(index)
            if ip and ip != "Select a device":
                self.selectedDevice["ipaddress"] = ip
                self.selectedDevice["client"]    = self.clients.get(ip)
                self.loadDeviceUsers()
        except Exception as e:
            Logger.error(f"[MainWindow] on_dropdown_device_selected: {e}")

    def filter_users_table(self, text: str):
        for row in range(self.usersModel.rowCount()):
            item = self.usersModel.item(row, 1)
            self.usersTableView.setRowHidden(row, text.lower() not in item.text().lower())

    # ── Settings tab ───────────────────────────────────────────────────

    def update_biometric_status(self):
        try:
            school_url = self.schoolURL.text()
            api_key    = self.apiKey.text()
            if not school_url or not api_key:
                return
            if school_url.strip().lower().startswith("http://"):
                Alert.show(self, "Please use HTTPS URL.", "Error")
                return
            api = APIHelper(school_url, apiKey=api_key)
            response = api.downloadConfig(returnResponse=True)
            if response:
                date = response.data.date or None
                if date:
                    today  = datetime.now().date()
                    server = datetime.strptime(date, "%Y-%m-%d").date()
                    if today != server:
                        Alert.show(self, "Date not synced with server. Update system date.", "Error")
        except Exception as e:
            Logger.error(f"[MainWindow] update_biometric_status: {e}")

    def on_download_config_click(self):
        try:
            school_url = self.schoolURL.text()
            api_key    = self.apiKey.text()
            if school_url.strip().lower().startswith("http://"):
                Alert.show(self, "Please use HTTPS URL.", "Error")
                return
            api = APIHelper(school_url, apiKey=api_key)
            if api.downloadConfig():
                self._controller.save_config("apiKey", api_key)
                self._controller.save_config("schoolURL", school_url)
                Alert.show(self, "Data Saved.")
            else:
                Alert.show(self, "Invalid URL or API Key", "Error")
        except Exception as e:
            Logger.error(f"[MainWindow] on_download_config_click: {e}")
            Alert.show(self, "Please provide a valid URL!")

    # ── Network scanning thread ─────────────────────────────────────────

    def startNetworkTread(self):
        if 7 in self.thread and self.thread[7] and self.thread[7].isRunning():
            return
        self.networkDevicesModel.removeRows(0, self.networkDevicesModel.rowCount())
        self.thread[7] = NetworkThread(parent=None, index=7)
        self.scanNetworkButton.setEnabled(False)
        self.thread[7].start()
        self.thread[7].stop_signal.connect(self.stopNetworkThread)
        self.thread[7].t_signal.connect(self.updateNetworkThreadResponse)
        self.thread[7].error_signal.connect(self.updateNetworkThreadErrorLog)
        self.thread[7].gateway_signal.connect(self.updateNetworkGatewayIp)
        self.thread[7].gateway_ip_signal.connect(self.updateNetworkGatewayIp)
        self.thread[7].device_signal.connect(self.updateNetworkThreadDevice)
        QApplication.setOverrideCursor(QCursor(QtCore.Qt.CursorShape.WaitCursor))

    def stopNetworkThread(self):
        QApplication.setOverrideCursor(QCursor(QtCore.Qt.CursorShape.ArrowCursor))
        self.scanNetworkButton.setEnabled(False)
        if self.thread.get(7):
            try:
                self.thread[7].stop()
                self.thread[7].wait()
            except Exception as e:
                Logger.error(f"[MainWindow] stopNetworkThread: {e}")
            self.thread[7].deleteLater()
            self.thread[7] = None
        self.scanNetworkButton.setEnabled(True)

    def updateNetworkThreadErrorLog(self, error: str):
        self.stopNetworkThread()

    def updateNetworkGatewayIp(self, ip: str):
        self.boxNetworkDevices.setTitle(f"Network Devices [{ip}]")

    def updateNetworkThreadResponse(self, text: str, color: str = ""):
        if self.sender().index == 7:
            pass   # extend if you have a network log browser

    def updateNetworkThreadDevice(self, ip: str, device_type: str):
        if self.sender().index == 7:
            items = [QStandardItem(str(f)) for f in [ip, device_type, ""]]
            self.networkDevicesModel.appendRow(items)
            self.networkDevicesTableView.horizontalHeader().setSectionResizeMode(
                QHeaderView.ResizeMode.Stretch
            )
