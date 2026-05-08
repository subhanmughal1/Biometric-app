"""
Main Controller
===============
Business logic layer. Sits between Views (UI) and Services (ZK devices).

Controller responsibilities:
  - Load/save devices from DeviceModel
  - Use ZKManager to talk to physical devices
  - Start/stop background threads
  - Update the View through signals (never touch UI widgets directly)
  - Keep Views "dumb" — Views only call controller methods

Rule: NO ZK SDK imports here. Only ZKManager + Models.
"""

from typing import Optional, Dict
from package.services.vendors.zkteco.zk_manager import ZKManager, ZkClient, DeviceType
from package.models.device_model import DeviceModel
from package.utils.logger import Logger
from package.config import ConfigHelper


class DeviceController:
    """
    Handles all device-related business logic.
    Used by MainWindow (View).
    """

    def __init__(self):
        self._zk_manager = ZKManager()
        self._device_model = DeviceModel()
        self._config = ConfigHelper()
        # ip → ZkClient (backward-compat cache for existing thread code)
        self._clients: Dict[str, ZkClient] = {}

    # ── Device CRUD ──────────────────────────────────────────────────

    def get_all_devices(self):
        """Return list of device dicts from database."""
        return self._device_model.get_all()

    def add_device(self, ip_address: str, name: str = "Biometric Device",
                   vendor: str = "ZKTeco") -> bool:
        """Add a new device to DB. Returns True if added, False if duplicate."""
        result = self._device_model.add_device(name, ip_address, vendor)
        return result is not None

    def remove_device(self, ip_address: str) -> None:
        """Remove device from DB and disconnect if connected."""
        self._device_model.remove_by_ip(ip_address)
        self._zk_manager.disconnect_device(ip_address)
        self._clients.pop(ip_address, None)

    # ── Connection ───────────────────────────────────────────────────

    def build_clients(self) -> Dict[str, ZkClient]:
        """
        Build ZkClient instances for all saved devices.
        Returns dict of {ip: ZkClient} — compatible with existing thread code.
        """
        self._clients = {}
        for device in self._device_model.get_all():
            ip = str(device["ipaddress"])
            self._clients[ip] = ZkClient(ipaddress=ip)
        return self._clients

    def get_clients(self) -> Dict[str, ZkClient]:
        return self._clients

    def get_client(self, ip: str) -> Optional[ZkClient]:
        return self._clients.get(ip)

    def is_device_connected(self, ip: str) -> bool:
        client = self._clients.get(ip)
        return bool(client and client.isConnected)

    # ── Device info ──────────────────────────────────────────────────

    def get_device_info(self, ip: str) -> Optional[dict]:
        """
        Returns device info dict for UI display.
        Uses raw conn so existing UI code still works.
        """
        client = self._clients.get(ip)
        if not client or not client.isConnected or not client.conn:
            return None
        try:
            return {
                "device_name":       str(client.conn.get_device_name()),
                "platform":          str(client.conn.get_platform()),
                "serial_number":     str(client.conn.get_serialnumber()),
                "firmware_version":  str(client.conn.get_firmware_version()),
                "gateway":           str(client.conn.get_network_params().get("gateway", "")),
                "mac_address":       str(client.conn.get_mac()),
                "time":              str(client.conn.get_time()),
            }
        except Exception as e:
            Logger.error(f"[DeviceController] get_device_info {ip}: {e}")
            return None

    # ── Device operations ────────────────────────────────────────────

    def restart_device(self, ip: str) -> bool:
        client = self._clients.get(ip)
        if client and client.isConnected:
            return client.restart()
        return False

    def clear_attendance(self, ip: str) -> bool:
        client = self._clients.get(ip)
        if client and client.isConnected:
            return client.clearAttendance()
        return False

    def clear_data(self, ip: str) -> bool:
        client = self._clients.get(ip)
        if client and client.isConnected:
            return client.clearData()
        return False

    # ── User operations ──────────────────────────────────────────────

    def get_device_users(self, ip: str):
        client = self._clients.get(ip)
        if client and client.isConnected:
            return client.getUsers() or []
        return []

    def get_date_attendance(self, ip: str, year=None, month=None, day=None):
        client = self._clients.get(ip)
        if client and client.isConnected:
            return client.getDateAttendance(year, month, day) or []
        return []

    def delete_device_user(self, ip: str, uid: int) -> bool:
        client = self._clients.get(ip)
        if client and client.isConnected:
            return client.deleteUser(uid)
        return False

    # ── Config ───────────────────────────────────────────────────────

    def get_config(self, key: str, default=None):
        return self._config.read_config(key, default)

    def save_config(self, key: str, value) -> None:
        self._config.write_config(key, value)
