"""
ZKTeco Hybrid Devices  ─  Face + Fingerprint + RFID
====================================================

This file contains ALL ZKTeco models that support face recognition
PLUS fingerprint PLUS RFID card simultaneously.

Models covered:
  ─ iFace302 / iFace302-Plus
  ─ iFace800 / iFace800-Plus
  ─ iFace700
  ─ iFace600
  ─ ProFace X  (full version with fingerprint)
  ─ SpeedFace-V5L[P]  (with fingerprint option)
  ─ G4 Pro
  ─ Palmsecure-F  (palm + face + card)
  ─ K40 Pro  (if firmware supports face)

All models in this file share:
  supports_fingerprint = True
  supports_face        = True
  supports_rfid        = True

Attendance type is dynamically resolved from verify_type per record.
"""

from datetime import datetime, timedelta
from typing import List, Optional

from package.services.vendors.zkteco.devices.base_zk_device import (
    BaseZKDevice, AttendanceRecord, DeviceUser, DeviceInfo, DeviceCapabilities
)
from package.utils.logger import Logger


# ─── Shared mixin for all full-hybrid devices ────────────────────────────────

class _FullHybridMixin:
    """
    Shared implementation for face + fingerprint + RFID devices.
    All these models behave identically at the SDK level.
    Mixed into each model class below.
    """

    CAPABILITIES = DeviceCapabilities(
        supports_fingerprint=True,
        supports_face=True,
        supports_rfid=True,
    )

    def get_attendance(self) -> List[AttendanceRecord]:
        records = []
        if not self.is_connected:
            return records
        for r in self._sdk.get_attendance():
            verify = getattr(r, "verify", 0) or 0
            records.append(AttendanceRecord(
                user_id=str(r.user_id),
                timestamp=r.timestamp,
                attendance_type=self._resolve_type(r.punch, verify),
                device_ip=self.ip,
                punch=r.punch,
                status=getattr(r, "status", 0),
                raw=r,
            ))
        return records

    def get_date_attendance(
        self,
        year: Optional[int] = None,
        month: Optional[int] = None,
        day: Optional[int] = None,
    ) -> List[AttendanceRecord]:
        year = year or datetime.now().year
        month = month or datetime.now().month
        day = day or datetime.now().day
        start = datetime(year, month, day, 0, 5)
        end = start + timedelta(days=1)
        records = []
        if not self.is_connected:
            return records
        for r in self._sdk.get_limited_attendance(start, end):
            verify = getattr(r, "verify", 0) or 0
            records.append(AttendanceRecord(
                user_id=str(r.user_id),
                timestamp=r.timestamp,
                attendance_type=self._resolve_type(r.punch, verify),
                device_ip=self.ip,
                punch=r.punch,
                status=getattr(r, "status", 0),
                raw=r,
            ))
        return records

    def get_users(self) -> List[DeviceUser]:
        return self._build_users()

    def get_device_info(self) -> Optional[DeviceInfo]:
        return self._build_device_info()

    def save_user(self, uid: int, name: str = "", password: str = "") -> bool:
        if not self.is_connected:
            return False
        try:
            uid_i = int(uid)
            if uid_i <= 0:
                return False
            name_s = str(name or "").encode("ascii", "ignore").decode().strip()[:24]
            return self._sdk.set_user(
                uid=uid_i, name=name_s,
                user_id=str(uid_i), password=str(password) if password else ""
            )
        except Exception as e:
            Logger.error(f"[{self.MODEL_NAME}] save_user uid={uid}: {e}")
            return False

    def delete_user(self, uid: int) -> bool:
        if not self.is_connected:
            return False
        return self._sdk.delete_user(int(uid))


# ───Individual model classes ────────────────────────────────────────────────

class IFace302(_FullHybridMixin, BaseZKDevice):
    """
    ZKTeco iFace302 / iFace302-Plus
    Fingerprint + Face + RFID card
    Common in offices and schools.
    """
    MODEL_NAME = "iFace302"


class IFace800(_FullHybridMixin, BaseZKDevice):
    """
    ZKTeco iFace800 / iFace800-Plus
    High-capacity: 8000 faces, 4000 fingerprints, RFID
    Used in large organizations.
    """
    MODEL_NAME = "iFace800"


class IFace700(_FullHybridMixin, BaseZKDevice):
    """
    ZKTeco iFace700
    Fingerprint + Face + Card
    Mid-range enterprise model.
    """
    MODEL_NAME = "iFace700"


class IFace600(_FullHybridMixin, BaseZKDevice):
    """
    ZKTeco iFace600
    Budget hybrid: fingerprint + face + RFID
    """
    MODEL_NAME = "iFace600"


class ProFaceX(_FullHybridMixin, BaseZKDevice):
    """
    ZKTeco ProFace X (full version with fingerprint module)
    AI face recognition + fingerprint + RFID
    """
    MODEL_NAME = "ProFace X"


class SpeedFaceV5LWithFP(_FullHybridMixin, BaseZKDevice):
    """
    ZKTeco SpeedFace-V5L[P] (with fingerprint)
    Large screen, AI face + fingerprint + RFID
    """
    MODEL_NAME = "SpeedFace-V5L[P]"


class G4Pro(_FullHybridMixin, BaseZKDevice):
    """
    ZKTeco G4 Pro
    Face + fingerprint + palm + RFID
    High-end multi-biometric device
    """
    MODEL_NAME = "G4 Pro"


class PalmSecureF(_FullHybridMixin, BaseZKDevice):
    """
    ZKTeco PalmSecure-F
    Palm vein + face + RFID
    Maps palm vein as fingerprint in SDK.
    """
    MODEL_NAME = "PalmSecure-F"


class GenericHybridDevice(_FullHybridMixin, BaseZKDevice):
    """
    Generic fallback for any ZKTeco device that supports
    fingerprint + face + RFID but doesn't match a specific model name.
    """
    MODEL_NAME = "GenericHybrid"


