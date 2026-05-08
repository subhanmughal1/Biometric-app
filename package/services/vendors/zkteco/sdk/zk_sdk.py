"""
ZKTeco SDK Wrapper
==================
This is the ONLY place in the codebase that imports from the 'zk' library.
All other code talks to ZKDevice through this SDK wrapper.

Responsibility: raw connection + raw data retrieval from ZK library.
Nothing else. No business logic here.
"""

from zk import ZK, const
from package.utils.logger import Logger


class ZKSdk:
    """
    Thin wrapper around the pyzk (zk) library.
    Manages raw TCP/UDP connection to a single ZKTeco device.
    Returns raw zk objects — normalization happens in device classes.
    """

    def __init__(self, ip: str, port: int = 4370, timeout: int = 5):
        self.ip = ip
        self.port = port
        self.timeout = timeout
        self._conn = None

    # ------------------------------------------------------------------
    # Connection
    # ------------------------------------------------------------------

    def connect(self) -> bool:
        """Try TCP first, fallback to UDP. Returns True on success."""
        # TCP attempt
        try:
            zk = ZK(self.ip, port=self.port, timeout=self.timeout,
                    force_udp=False, ommit_ping=True)
            conn = zk.connect()
            if conn:
                self._conn = conn
                Logger.info(f"[ZKSdk] {self.ip} connected via TCP")
                return True
        except Exception as e:
            Logger.error(f"[ZKSdk] {self.ip} TCP failed: {e}")

        # UDP fallback
        try:
            zk = ZK(self.ip, port=self.port, timeout=self.timeout,
                    force_udp=True, ommit_ping=True)
            conn = zk.connect()
            if conn:
                self._conn = conn
                Logger.info(f"[ZKSdk] {self.ip} connected via UDP")
                return True
        except Exception as e:
            Logger.error(f"[ZKSdk] {self.ip} UDP failed: {e}")

        return False

    def disconnect(self) -> None:
        try:
            if self._conn:
                self._conn.disconnect()
        except Exception as e:
            Logger.error(f"[ZKSdk] {self.ip} disconnect error: {e}")
        finally:
            self._conn = None

    @property
    def is_connected(self) -> bool:
        return self._conn is not None

    @property
    def raw_conn(self):
        """Raw zk connection — used for live_capture and special ops."""
        return self._conn

    # ------------------------------------------------------------------
    # Raw data reads  (return raw zk objects, no normalization)
    # ------------------------------------------------------------------

    def get_attendance(self):
        """Returns raw zk attendance list or []."""
        try:
            return self._conn.get_attendance() or []
        except Exception as e:
            Logger.error(f"[ZKSdk] {self.ip} get_attendance: {e}")
            return []

    def get_limited_attendance(self, start_date, end_date):
        """Returns date-filtered raw zk attendance list or []."""
        try:
            return self._conn.get_limited_attendance(
                start_date=start_date, end_date=end_date
            ) or []
        except Exception as e:
            Logger.error(f"[ZKSdk] {self.ip} get_limited_attendance: {e}")
            return []

    def get_users(self):
        """Returns raw zk user list or []."""
        try:
            return self._conn.get_users() or []
        except Exception as e:
            Logger.error(f"[ZKSdk] {self.ip} get_users: {e}")
            return []

    def set_user(self, uid: int, name: str, user_id: str, password: str = "",
                 privilege=None, group_id: str = "1", card: int = 0) -> bool:
        try:
            if privilege is None:
                privilege = const.USER_DEFAULT
            self._conn.set_user(
                uid=uid, name=name, privilege=privilege,
                group_id=group_id, user_id=user_id,
                password=password, card=card,
            )
            return True
        except Exception as e:
            Logger.error(f"[ZKSdk] {self.ip} set_user uid={uid}: {e}")
            return False

    def delete_user(self, uid: int) -> bool:
        try:
            return bool(self._conn.delete_user(uid=uid))
        except Exception as e:
            Logger.error(f"[ZKSdk] {self.ip} delete_user: {e}")
            return False

    # ------------------------------------------------------------------
    # Device info reads
    # ------------------------------------------------------------------

    def get_device_name(self) -> str:
        try:
            return self._conn.get_device_name() or ""
        except Exception:
            return ""

    def get_platform(self) -> str:
        try:
            return self._conn.get_platform() or ""
        except Exception:
            return ""

    def get_serialnumber(self) -> str:
        try:
            return self._conn.get_serialnumber() or ""
        except Exception:
            return ""

    def get_firmware_version(self) -> str:
        try:
            return self._conn.get_firmware_version() or ""
        except Exception:
            return ""

    def get_mac(self) -> str:
        try:
            return self._conn.get_mac() or ""
        except Exception:
            return ""

    def get_time(self) -> str:
        try:
            return str(self._conn.get_time())
        except Exception:
            return ""

    def get_network_params(self) -> dict:
        try:
            return self._conn.get_network_params() or {}
        except Exception:
            return {}

    def get_fp_version(self) -> str:
        try:
            return self._conn.get_fp_version() or ""
        except Exception:
            return ""

    def get_face_version(self) -> str:
        try:
            return self._conn.get_face_version() or ""
        except Exception:
            return ""

    # ------------------------------------------------------------------
    # Device control
    # ------------------------------------------------------------------

    def restart(self) -> bool:
        try:
            self._conn.restart()
            return True
        except Exception as e:
            Logger.error(f"[ZKSdk] {self.ip} restart: {e}")
            return False

    def clear_attendance(self) -> bool:
        try:
            self._conn.clear_attendance()
            return True
        except Exception as e:
            Logger.error(f"[ZKSdk] {self.ip} clear_attendance: {e}")
            return False

    def clear_data(self) -> bool:
        try:
            self._conn.clear_data()
            return True
        except Exception as e:
            Logger.error(f"[ZKSdk] {self.ip} clear_data: {e}")
            return False

    def disable_device(self) -> bool:
        try:
            self._conn.disable_device()
            return True
        except Exception as e:
            Logger.error(f"[ZKSdk] {self.ip} disable_device: {e}")
            return False

    def enable_device(self) -> bool:
        try:
            self._conn.enable_device()
            return True
        except Exception as e:
            Logger.error(f"[ZKSdk] {self.ip} enable_device: {e}")
            return False

    def live_capture(self, timeout: int = 10):
        """Raw live capture generator — yields raw zk events."""
        try:
            yield from self._conn.live_capture(timeout)
        except Exception as e:
            Logger.error(f"[ZKSdk] {self.ip} live_capture: {e}")
