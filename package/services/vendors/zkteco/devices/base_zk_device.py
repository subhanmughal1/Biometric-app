"""
Base ZK Device
==============
Abstract base class every ZKTeco device model must inherit from.
Defines the contract: what every device MUST implement.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Any

from package.services.vendors.zkteco.sdk.zk_sdk import ZKSdk
from package.utils.logger import Logger


# ── Shared data structures ──────────────────────────────────────────────────

@dataclass
class AttendanceRecord:
    """
    Normalized attendance record returned by every device model.

    attendance_type is limited to what the device actually supports:
      'fingerprint' | 'face' | 'card' | 'unknown'
    """
    user_id: str
    timestamp: datetime
    attendance_type: str        # fingerprint / face / card / unknown
    device_ip: str
    punch: int = 0              # 0=check-in  1=check-out  4=OT-in  5=OT-out
    status: int = 0
    raw: Any = field(default=None, repr=False)   # original zk object


@dataclass
class DeviceUser:
    uid: int
    user_id: str
    name: str
    privilege: int = 0
    card: int = 0


@dataclass
class DeviceInfo:
    serial_number: str = ""
    firmware_version: str = ""
    device_name: str = ""
    platform: str = ""
    face_algorithm_version: str = ""
    fingerprint_algorithm_version: str = ""
    mac_address: str = ""
    time: str = ""
    gateway: str = ""


@dataclass
class DeviceCapabilities:
    """Declares exactly what a device model supports."""
    supports_fingerprint: bool = False
    supports_face: bool = False
    supports_rfid: bool = False

    @property
    def supported_types(self) -> List[str]:
        types = []
        if self.supports_fingerprint:
            types.append("fingerprint")
        if self.supports_face:
            types.append("face")
        if self.supports_rfid:
            types.append("card")
        return types or ["unknown"]


# ── Abstract base ────────────────────────────────────────────────────────────

class BaseZKDevice(ABC):
    """
    Every ZKTeco device model inherits from this.

    Subclass responsibilities:
      1. Set MODEL_NAME, CAPABILITIES
      2. Implement all @abstractmethod methods
      3. Only produce attendance_type values declared in CAPABILITIES
    """

    MODEL_NAME: str = "BaseZKDevice"
    CAPABILITIES: DeviceCapabilities = DeviceCapabilities()

    def __init__(self, ip: str, port: int = 4370, timeout: int = 5):
        self.ip = ip
        self.port = port
        self.timeout = timeout
        self.is_connected: bool = False
        self._sdk: ZKSdk = ZKSdk(ip, port, timeout)

    # ── Connection ────────────────────────────────────────────────────

    def connect(self) -> bool:
        """Connect using SDK. Sets self.is_connected."""
        result = self._sdk.connect()
        self.is_connected = result
        return result

    def disconnect(self) -> None:
        """Disconnect cleanly."""
        self._sdk.disconnect()
        self.is_connected = False

    # ── Core methods (must implement) ─────────────────────────────────

    @abstractmethod
    def get_attendance(self) -> List[AttendanceRecord]:
        """Return all attendance records, normalized."""
        ...

    @abstractmethod
    def get_date_attendance(
        self,
        year: Optional[int] = None,
        month: Optional[int] = None,
        day: Optional[int] = None,
    ) -> List[AttendanceRecord]:
        """Return attendance for a specific date."""
        ...

    @abstractmethod
    def get_users(self) -> List[DeviceUser]:
        """Return all enrolled users."""
        ...

    @abstractmethod
    def get_device_info(self) -> Optional[DeviceInfo]:
        """Return device information."""
        ...

    # ── Optional methods (override if device supports it) ─────────────

    def save_user(self, uid: int, name: str = "", password: str = "") -> bool:
        Logger.error(f"[{self.MODEL_NAME}] save_user not supported")
        return False

    def delete_user(self, uid: int) -> bool:
        Logger.error(f"[{self.MODEL_NAME}] delete_user not supported")
        return False

    def restart(self) -> bool:
        return self._sdk.restart()

    def clear_attendance(self) -> bool:
        return self._sdk.clear_attendance()

    def clear_data(self) -> bool:
        return self._sdk.clear_data()

    def disable_device(self) -> bool:
        return self._sdk.disable_device()

    def enable_device(self) -> bool:
        return self._sdk.enable_device()

    def live_capture(self, timeout: int = 10):
        """Generator yielding AttendanceRecord from live events."""
        for raw_event in self._sdk.live_capture(timeout):
            if raw_event is None:
                yield None
                continue
            verify = getattr(raw_event, "verify", 0) or 0
            att_type = self._resolve_type(raw_event.punch, verify)
            yield AttendanceRecord(
                user_id=str(raw_event.user_id),
                timestamp=raw_event.timestamp,
                attendance_type=att_type,
                device_ip=self.ip,
                punch=raw_event.punch,
                status=getattr(raw_event, "status", 0),
                raw=raw_event,
            )

    # ── Capabilities ──────────────────────────────────────────────────

    def capabilities(self) -> DeviceCapabilities:
        return self.CAPABILITIES

    # ── Shared utility ────────────────────────────────────────────────

    def _resolve_type(self, punch: int, verify_type: int) -> str:
        """
        Map raw verify_type → normalized attendance_type.
        Constrained to device CAPABILITIES.

        ZK verify_type reference:
            0–5  = fingerprint
            6    = RFID card
            10+  = face recognition
        """
        caps = self.CAPABILITIES
        if verify_type == 6:
            raw = "card"
        elif verify_type >= 10:
            raw = "face"
        else:
            raw = "fingerprint"

        if raw == "card" and caps.supports_rfid:
            return "card"
        if raw == "face" and caps.supports_face:
            return "face"
        if raw == "fingerprint" and caps.supports_fingerprint:
            return "fingerprint"

        # fallback to first supported type
        return caps.supported_types[0]

    def _build_users(self) -> List[DeviceUser]:
        """Helper: fetch + normalize users from SDK."""
        users = []
        for u in self._sdk.get_users():
            users.append(DeviceUser(
                uid=u.uid,
                user_id=str(u.user_id),
                name=u.name,
                privilege=u.privilege,
                card=getattr(u, "card", 0),
            ))
        return users

    def _build_device_info(self) -> Optional[DeviceInfo]:
        """Helper: fetch device info from SDK."""
        if not self.is_connected:
            return None
        return DeviceInfo(
            serial_number=self._sdk.get_serialnumber(),
            firmware_version=self._sdk.get_firmware_version(),
            device_name=self._sdk.get_device_name(),
            platform=self._sdk.get_platform(),
            face_algorithm_version=self._sdk.get_face_version(),
            fingerprint_algorithm_version=self._sdk.get_fp_version(),
            mac_address=self._sdk.get_mac(),
            time=self._sdk.get_time(),
            gateway=self._sdk.get_network_params().get("gateway", ""),
        )

    def __repr__(self) -> str:
        s = "connected" if self.is_connected else "disconnected"
        c = self.CAPABILITIES
        return (
            f"<{self.MODEL_NAME} ip={self.ip} {s} "
            f"fp={c.supports_fingerprint} face={c.supports_face} rfid={c.supports_rfid}>"
        )
