"""
Models Layer - DeviceModel
===========================
Pure data layer. No PyQt. No ZK SDK. No HTTP.
Talks to SQLite via DbHelper.
"""

from typing import Optional, List
from package.utils.db import DbHelper


class DeviceModel(DbHelper):
    """Represents the 'devices' table."""
    tableName = "devices"

    def __init__(self, debug: bool = False):
        super().__init__("", debug)

    def add_device(self, name: str, ip_address: str, vendor: str = "ZKTeco",
                   port: int = 4370, serial_number: str = "") -> Optional[int]:
        """Add device. Returns new row id, or None if IP already exists."""
        if self.records("*", f"ipaddress='{ip_address}'", None, True) > 0:
            return None
        return self.add({
            "name":          name,
            "ipaddress":     ip_address,
            "port":          port,
            "vendor":        vendor,
            "serial_number": serial_number,
        })

    def update_device(self, rid: int, **fields) -> None:
        if fields:
            self.save(rid, fields)

    def get_all(self) -> List[dict]:
        return self.records()

    def get_by_ip(self, ip_address: str) -> Optional[dict]:
        return self.select_one(self.tableName, "*", "ipaddress=?", (ip_address,))

    def remove_by_ip(self, ip_address: str) -> None:
        self.remove_where("ipaddress=?", (ip_address,))
