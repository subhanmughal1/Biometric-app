"""
ZK Manager
==========
Central ZKTeco service. This is what Controllers call.

Responsibilities:
  - Device registry (model name → class mapping)
  - Auto-detect device type from device name
  - Manage multiple connected devices
  - Provide unified interface: get_device(), get_date_attendance_from_all() etc.
  - Backward-compatible ZkClient / ZkHelper shims so old code keeps working
"""




from typing import Dict, List, Optional, Type
from zk import ZK

from package.services.vendors.zkteco.devices.base_zk_device import (
    BaseZKDevice, AttendanceRecord, DeviceUser, DeviceInfo, DeviceCapabilities
)
from package.services.vendors.zkteco.devices.hybrid.full_hybrid_devices import (
    IFace302, IFace800, IFace700, IFace600,
    ProFaceX, SpeedFaceV5LWithFP, G4Pro, PalmSecureF, GenericHybridDevice,
)
from package.services.vendors.zkteco.devices.standard.standard_devices import (
    K40, K40Pro, K20, K20Pro, F18, F18Plus, F22, F22Plus, F6Plus,
    IClock360, IClock560, IClock680, MA300, TX628, K10, K14,
    SilkBio100TC, ZK4500, LX14, GenericStandardDevice,
)
from package.utils.logger import Logger


# ── Device type constants ────────────────────────────────────────────────────

class DeviceType:
    # Hybrid (face + fingerprint + RFID)
    IFACE302            = "iface302"
    IFACE800            = "iface800"
    IFACE700            = "iface700"
    IFACE600            = "iface600"
    PROFACE_X           = "proface_x"
    SPEEDFACE_V5L_P     = "speedface_v5l_p"
    G4_PRO              = "g4_pro"
    PALMSECURE_F        = "palmsecure_f"
    GENERIC_HYBRID      = "generic_hybrid"

    # Standard (fingerprint + RFID, no face)
    K40                 = "k40"
    K40_PRO             = "k40_pro"
    K20                 = "k20"
    K20_PRO             = "k20_pro"
    F18                 = "f18"
    F18_PLUS            = "f18_plus"
    F22                 = "f22"
    F22_PLUS            = "f22_plus"
    F6_PLUS             = "f6_plus"
    ICLOCK360           = "iclock360"
    ICLOCK560           = "iclock560"
    ICLOCK680           = "iclock680"
    MA300               = "ma300"
    TX628               = "tx628"
    K10                 = "k10"
    K14                 = "k14"
    SILKBIO             = "silkbio"
    ZK4500              = "zk4500"
    LX14                = "lx14"
    GENERIC_STANDARD    = "generic_standard"

    # Auto-detect
    AUTO                = "auto"


# ── Registry: device type → class ────────────────────────────────────────────

DEVICE_REGISTRY: Dict[str, Type[BaseZKDevice]] = {
    # Hybrid
    DeviceType.IFACE302:          IFace302,
    DeviceType.IFACE800:          IFace800,
    DeviceType.IFACE700:          IFace700,
    DeviceType.IFACE600:          IFace600,
    DeviceType.PROFACE_X:         ProFaceX,
    DeviceType.SPEEDFACE_V5L_P:   SpeedFaceV5LWithFP,
    DeviceType.G4_PRO:            G4Pro,
    DeviceType.PALMSECURE_F:      PalmSecureF,
    DeviceType.GENERIC_HYBRID:    GenericHybridDevice,
    # Standard
    DeviceType.K40:               K40,
    DeviceType.K40_PRO:           K40Pro,
    DeviceType.K20:               K20,
    DeviceType.K20_PRO:           K20Pro,
    DeviceType.F18:               F18,
    DeviceType.F18_PLUS:          F18Plus,
    DeviceType.F22:               F22,
    DeviceType.F22_PLUS:          F22Plus,
    DeviceType.F6_PLUS:           F6Plus,
    DeviceType.ICLOCK360:         IClock360,
    DeviceType.ICLOCK560:         IClock560,
    DeviceType.ICLOCK680:         IClock680,
    DeviceType.MA300:             MA300,
    DeviceType.TX628:             TX628,
    DeviceType.K10:               K10,
    DeviceType.K14:               K14,
    DeviceType.SILKBIO:           SilkBio100TC,
    DeviceType.ZK4500:            ZK4500,
    DeviceType.LX14:              LX14,
    DeviceType.GENERIC_STANDARD:  GenericStandardDevice,
}

# ── Auto-detection: device name keyword → DeviceType ──────────────────────────

_NAME_MAP: Dict[str, str] = {
    # Hybrid
    "iface302":         DeviceType.IFACE302,
    "iface800":         DeviceType.IFACE800,
    "iface700":         DeviceType.IFACE700,
    "iface600":         DeviceType.IFACE600,
    "proface x":        DeviceType.PROFACE_X,
    "speedface-v5l[p]": DeviceType.SPEEDFACE_V5L_P,
    "g4 pro":           DeviceType.G4_PRO,
    "palmsecure":       DeviceType.PALMSECURE_F,

    # Standard
    "k40 pro":          DeviceType.K40_PRO,
    "k40":              DeviceType.K40,
    "k20 pro":          DeviceType.K20_PRO,
    "k20":              DeviceType.K20,
    "f18-plus":         DeviceType.F18_PLUS,
    "f18":              DeviceType.F18,
    "f22-plus":         DeviceType.F22_PLUS,
    "f22":              DeviceType.F22,
    "f6 plus":          DeviceType.F6_PLUS,
    "iclock360":        DeviceType.ICLOCK360,
    "iclock560":        DeviceType.ICLOCK560,
    "iclock680":        DeviceType.ICLOCK680,
    "ma300":            DeviceType.MA300,
    "tx628":            DeviceType.TX628,
    "k10":              DeviceType.K10,
    "k14":              DeviceType.K14,
    "silkbio":          DeviceType.SILKBIO,
    "zk4500":           DeviceType.ZK4500,
    "lx14":             DeviceType.LX14,
}


# ── ZKManager ─────────────────────────────────────────────────────────────────

class ZKManager:
    """
    Central ZKTeco service used by Controllers.

    Usage:
        manager = ZKManager()
        device = manager.get_device("192.168.1.201")
        if device and device.is_connected:
            records = device.get_date_attendance()
        manager.disconnect_all()
    """

    def __init__(self, default_port: int = 4370, default_timeout: int = 5):
        self.default_port = default_port
        self.default_timeout = default_timeout
        self._pool: Dict[str, BaseZKDevice] = {}   # ip → device instance

    # ── Public API ─────────────────────────────────────────────────────

    def get_device(
        self,
        ip: str,
        device_type: str = DeviceType.AUTO,
        timeout: Optional[int] = None,
        force_reconnect: bool = False,
    ) -> Optional[BaseZKDevice]:
        """
        Return a connected device instance.
        Uses cached instance if still connected (unless force_reconnect=True).
        """
        timeout = timeout or self.default_timeout

        if ip in self._pool and not force_reconnect:
            if self._pool[ip].is_connected:
                return self._pool[ip]

        # Determine class
        if device_type == DeviceType.AUTO:
            cls = self._auto_detect(ip, timeout)
        else:
            cls = DEVICE_REGISTRY.get(device_type, GenericStandardDevice)

        device = cls(ip=ip, port=self.default_port, timeout=timeout)
        if device.connect():
            self._pool[ip] = device
            Logger.info(
                f"[ZKManager] {ip} → {device.MODEL_NAME} "
                f"caps={device.capabilities().supported_types}"
            )
            return device

        Logger.error(f"[ZKManager] {ip} connection failed")
        return None

    def disconnect_device(self, ip: str) -> None:
        dev = self._pool.pop(ip, None)
        if dev:
            dev.disconnect()

    def disconnect_all(self) -> None:
        for ip, dev in list(self._pool.items()):
            try:
                dev.disconnect()
            except Exception as e:
                Logger.error(f"[ZKManager] disconnect error {ip}: {e}")
        self._pool.clear()

    def connected_ips(self) -> List[str]:
        return [ip for ip, d in self._pool.items() if d.is_connected]

    def get_date_attendance_from_all(
        self,
        ip_list: List[str],
        year: Optional[int] = None,
        month: Optional[int] = None,
        day: Optional[int] = None,
        timeout: int = 90,
    ) -> Dict[str, List[AttendanceRecord]]:
        """Fetch date attendance from multiple devices. Returns {ip: [records]}."""
        result = {}
        for ip in ip_list:
            dev = self.get_device(ip, timeout=timeout)
            if dev and dev.is_connected:
                result[ip] = dev.get_date_attendance(year=year, month=month, day=day)
            else:
                result[ip] = []
        return result

    @staticmethod
    def is_zk_device(ip: str, port: int = 4370, timeout: int = 5) -> bool:
        """Quick probe to check if IP is a ZKTeco device."""
        conn = None
        try:
            zk = ZK(ip, port=port, timeout=timeout,
                    password=0, force_udp=False, ommit_ping=False)
            conn = zk.connect()
            return bool(conn)
        except Exception as e:
            Logger.error(f"[ZKManager] is_zk_device {ip}: {e}")
            return False
        finally:
            if conn:
                try:
                    conn.disconnect()
                except Exception:
                    pass

    # ── Internal ───────────────────────────────────────────────────────

    def _auto_detect(self, ip: str, timeout: int) -> Type[BaseZKDevice]:
        """Probe device, read name, return best matching class."""
        conn = None
        name = ""
        try:
            from zk import ZK
            zk = ZK(ip, port=self.default_port, timeout=timeout,
                    force_udp=False, ommit_ping=True)
            conn = zk.connect()
            if conn:
                name = (conn.get_device_name() or "").strip().lower()
        except Exception:
            pass
        finally:
            if conn:
                try:
                    conn.disconnect()
                except Exception:
                    pass

        if name:
            for keyword, dtype in _NAME_MAP.items():
                if keyword in name:
                    Logger.info(f"[ZKManager] auto-detected '{name}' → {dtype}")
                    return DEVICE_REGISTRY[dtype]

        Logger.info(f"[ZKManager] '{name}' unrecognized → GenericStandard")
        return GenericStandardDevice


# ── Backward-compatible shims ─────────────────────────────────────────────────
# Old code (attendance_manager.py, data_manager.py, network_thread.py)
# imports ZkClient and ZkHelper from package.utils.zkclient.
# We keep those imports working by providing shims here too.
# The new zkclient.py will simply re-export these.

class ZkHelper:
    """Drop-in replacement for old ZkHelper."""

    @staticmethod
    def isZkDevice(ipaddress: str, port: int = 4370, timeout: int = 5) -> bool:
        return ZKManager.is_zk_device(ipaddress, port=port, timeout=timeout)


class ZkClient:
    """
    Drop-in replacement for old ZkClient.
    Controllers / Managers that haven't been migrated yet
    can continue using this with NO code changes.
    """

    def __init__(
        self,
        ipaddress: str = "192.168.1.201",
        timeout: int = 5,
        port: int = 4370,
        device_type: str = DeviceType.AUTO,
    ):
        self.ipAddress = ipaddress
        _manager = ZKManager(default_port=port, default_timeout=timeout)
        self._device: Optional[BaseZKDevice] = _manager.get_device(
            ipaddress, device_type=device_type, timeout=timeout
        )
        self.isConnected: bool = bool(self._device and self._device.is_connected)
        # Expose raw conn for callers that use client.conn.xyz directly
        self.conn = self._device._sdk.raw_conn if self._device else None

    def getAttendance(self):
        if not self._device:
            return None
        return [r.raw for r in self._device.get_attendance() if r.raw] or None

    def getDateAttendance(self, year=None, month=None, day=None):
        if not self._device:
            return None
        return [r.raw for r in self._device.get_date_attendance(year, month, day) if r.raw] or None

    def getUsers(self):
        if not self._device:
            return None
        return self._device._sdk.get_users() or None

    def saveUser(self, uid, name="", password="") -> bool:
        return self._device.save_user(uid, name, password) if self._device else False

    def deleteUser(self, uid) -> bool:
        return self._device.delete_user(uid) if self._device else False

    def clearAttendance(self) -> bool:
        return self._device.clear_attendance() if self._device else False

    def clearData(self) -> bool:
        return self._device.clear_data() if self._device else False

    def restart(self) -> bool:
        return self._device.restart() if self._device else False

    def disconnect(self) -> None:
        if self._device:
            self._device.disconnect()
        self.isConnected = False
        self.conn = None
