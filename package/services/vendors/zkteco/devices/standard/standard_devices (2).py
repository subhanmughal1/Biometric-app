"""
ZKTeco Standard Devices  ─  Fingerprint + RFID  (NO Face Recognition)
======================================================================

This file contains ALL ZKTeco models that support fingerprint + RFID card
but do NOT have face recognition capability.

Models covered:
  ─ K40 / K40 Pro  (fingerprint only variant)
  ─ K20 / K20 Pro
  ─ F18 / F18-Plus
  ─ F22 / F22-Plus
  ─ iClock360
  ─ iClock560
  ─ iClock680
  ─ MA300 (fingerprint + RFID)
  ─ SilkBio-100TC
  ─ LX14 (standalone fingerprint)
  ─ ZK4500 (PC-connected fingerprint reader)
  ─ F6 Plus
  ─ K10 / K14
  ─ TX628

All models share:
  supports_fingerprint = True
  supports_face        = False
  supports_rfid        = True  (most models; see FingerprintOnlyMixin for pure FP)

Note: Pure fingerprint-only models (no card reader) also use this file
      with supports_rfid=False set explicitly.
"""

from datetime import datetime, timedelta
from typing import List, Optional

from package.services.vendors.zkteco.devices.base_zk_device import (
    BaseZKDevice, AttendanceRecord, DeviceUser, DeviceInfo, DeviceCapabilities
)
from package.utils.logger import Logger


# ─── Mixin: Fingerprint + RFID (no face) ────────────────────────────────────

class _FingerprintRFIDMixin:
    """
    Shared implementation for fingerprint + RFID devices without face.
    Attendance type is always 'fingerprint' or 'card' — never 'face'.
    """

    CAPABILITIES = DeviceCapabilities(
        supports_fingerprint=True,
        supports_face=False,
        supports_rfid=True,
    )

    def get_attendance(self) -> List[AttendanceRecord]:
        records = []
        if not self.is_connected:
            return records
        for r in self._sdk.get_attendance():
            verify = getattr(r, "verify", 0) or 0
            # verify=6 → card, anything else → fingerprint
            att_type = "card" if verify == 6 else "fingerprint"
            records.append(AttendanceRecord(
                user_id=str(r.user_id),
                timestamp=r.timestamp,
                attendance_type=att_type,
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
            att_type = "card" if verify == 6 else "fingerprint"
            records.append(AttendanceRecord(
                user_id=str(r.user_id),
                timestamp=r.timestamp,
                attendance_type=att_type,
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


# ─── Mixin: Fingerprint ONLY (no card, no face) ──────────────────────────────

class _FingerprintOnlyMixin(_FingerprintRFIDMixin):
    """For pure fingerprint devices that have no card reader slot."""

    CAPABILITIES = DeviceCapabilities(
        supports_fingerprint=True,
        supports_face=False,
        supports_rfid=False,
    )

    def get_attendance(self) -> List[AttendanceRecord]:
        records = []
        if not self.is_connected:
            return records
        for r in self._sdk.get_attendance():
            records.append(AttendanceRecord(
                user_id=str(r.user_id),
                timestamp=r.timestamp,
                attendance_type="fingerprint",   # always FP
                device_ip=self.ip,
                punch=r.punch,
                status=getattr(r, "status", 0),
                raw=r,
            ))
        return records

    def get_date_attendance(self, year=None, month=None, day=None) -> List[AttendanceRecord]:
        year = year or datetime.now().year
        month = month or datetime.now().month
        day = day or datetime.now().day
        start = datetime(year, month, day, 0, 5)
        end = start + timedelta(days=1)
        records = []
        if not self.is_connected:
            return records
        for r in self._sdk.get_limited_attendance(start, end):
            records.append(AttendanceRecord(
                user_id=str(r.user_id),
                timestamp=r.timestamp,
                attendance_type="fingerprint",
                device_ip=self.ip,
                punch=r.punch,
                status=getattr(r, "status", 0),
                raw=r,
            ))
        return records


# ─── Model classes: Fingerprint + RFID ───────────────────────────────────────

class K40(_FingerprintRFIDMixin, BaseZKDevice):
    """
    ZKTeco K40
    Optical fingerprint + RFID card
    Very common in Pakistan / South Asia schools
    """
    MODEL_NAME = "K40"


class K40Pro(_FingerprintRFIDMixin, BaseZKDevice):
    """ZKTeco K40 Pro — upgraded K40 with larger capacity."""
    MODEL_NAME = "K40 Pro"


class K20(_FingerprintRFIDMixin, BaseZKDevice):
    """ZKTeco K20 — budget fingerprint + card reader."""
    MODEL_NAME = "K20"


class K20Pro(_FingerprintRFIDMixin, BaseZKDevice):
    """ZKTeco K20 Pro."""
    MODEL_NAME = "K20 Pro"


class F18(_FingerprintRFIDMixin, BaseZKDevice):
    """
    ZKTeco F18 / F18-Plus
    Fingerprint + RFID, colorful display
    Popular entry-level model
    """
    MODEL_NAME = "F18"


class F18Plus(_FingerprintRFIDMixin, BaseZKDevice):
    """ZKTeco F18-Plus."""
    MODEL_NAME = "F18-Plus"


class F22(_FingerprintRFIDMixin, BaseZKDevice):
    """ZKTeco F22 / F22-Plus — mid-range fingerprint + RFID."""
    MODEL_NAME = "F22"


class F22Plus(_FingerprintRFIDMixin, BaseZKDevice):
    """ZKTeco F22-Plus."""
    MODEL_NAME = "F22-Plus"


class F6Plus(_FingerprintRFIDMixin, BaseZKDevice):
    """ZKTeco F6 Plus — compact fingerprint + card."""
    MODEL_NAME = "F6 Plus"


class IClock360(_FingerprintRFIDMixin, BaseZKDevice):
    """
    ZKTeco iClock360
    Classic fingerprint + RFID terminal
    Very widely deployed in Pakistan
    """
    MODEL_NAME = "iClock360"


class IClock560(_FingerprintRFIDMixin, BaseZKDevice):
    """ZKTeco iClock560 — larger capacity version of 360."""
    MODEL_NAME = "iClock560"


class IClock680(_FingerprintRFIDMixin, BaseZKDevice):
    """ZKTeco iClock680."""
    MODEL_NAME = "iClock680"


class MA300(_FingerprintRFIDMixin, BaseZKDevice):
    """
    ZKTeco MA300
    Waterproof outdoor fingerprint + RFID
    Used for factory/outdoor environments
    """
    MODEL_NAME = "MA300"


class TX628(_FingerprintRFIDMixin, BaseZKDevice):
    """ZKTeco TX628 — fingerprint + RFID, older model."""
    MODEL_NAME = "TX628"


class K10(_FingerprintRFIDMixin, BaseZKDevice):
    """ZKTeco K10."""
    MODEL_NAME = "K10"


class K14(_FingerprintRFIDMixin, BaseZKDevice):
    """ZKTeco K14."""
    MODEL_NAME = "K14"


# ─── Model classes: Fingerprint ONLY (no RFID) ───────────────────────────────

class SilkBio100TC(_FingerprintOnlyMixin, BaseZKDevice):
    """
    ZKTeco SilkBio-100TC
    Capacitive fingerprint ONLY, no card reader
    """
    MODEL_NAME = "SilkBio-100TC"


class ZK4500(_FingerprintOnlyMixin, BaseZKDevice):
    """
    ZKTeco ZK4500
    USB fingerprint reader (PC-connected).
    Treated as network device when used with ZKTeco middleware.
    """
    MODEL_NAME = "ZK4500"


class LX14(_FingerprintOnlyMixin, BaseZKDevice):
    """ZKTeco LX14 — simple fingerprint-only terminal."""
    MODEL_NAME = "LX14"


# ─── Generic fallback ────────────────────────────────────────────────────────

class GenericStandardDevice(_FingerprintRFIDMixin, BaseZKDevice):
    """
    Generic fallback for any ZKTeco device with fingerprint + RFID
    that doesn't match a specific model name.
    """
    MODEL_NAME = "GenericStandard"



