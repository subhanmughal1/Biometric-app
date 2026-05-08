import sys, os
from pathlib import Path


def data_dir():

    # Get the path to the user's Local AppData directory
    app_data_dir = Path(os.getenv("LOCALAPPDATA")) / "BioAttendance"
    app_data_dir.mkdir(parents=True, exist_ok=True)  # Create the directory if it doesn't exist
    return app_data_dir
     

DATA_DIR = data_dir()
ROOT_DIR = os.path.dirname(os.path.realpath(__file__))
# modify the root directory in freezed program
if getattr(sys, "frozen", False):
    ROOT_DIR = os.path.dirname(sys.executable)


def _show_msgbox_error(title: str, msg: str) -> None:
    try:
        import ctypes
        MB_ICONERROR = 0x10
        MB_TOPMOST = 0x40000
        ctypes.windll.user32.MessageBoxW(0, msg, title, MB_ICONERROR | MB_TOPMOST)
    except Exception:
        print(msg, file=sys.stderr)


def _get_real_windows_version():
    """
    Returns (major, minor, build) using RtlGetVersion (more reliable than
    sys.getwindowsversion() under compatibility mode).
    """
    try:
        import ctypes

        class OSVERSIONINFOEXW(ctypes.Structure):
            _fields_ = [
                ("dwOSVersionInfoSize", ctypes.c_ulong),
                ("dwMajorVersion", ctypes.c_ulong),
                ("dwMinorVersion", ctypes.c_ulong),
                ("dwBuildNumber", ctypes.c_ulong),
                ("dwPlatformId", ctypes.c_ulong),
                ("szCSDVersion", ctypes.c_wchar * 128),
                ("wServicePackMajor", ctypes.c_ushort),
                ("wServicePackMinor", ctypes.c_ushort),
                ("wSuiteMask", ctypes.c_ushort),
                ("wProductType", ctypes.c_byte),
                ("wReserved", ctypes.c_byte),
            ]

        ntdll = ctypes.windll.ntdll
        osvi = OSVERSIONINFOEXW()
        osvi.dwOSVersionInfoSize = ctypes.sizeof(OSVERSIONINFOEXW)

        # RtlGetVersion returns 0 on success
        if ntdll.RtlGetVersion(ctypes.byref(osvi)) == 0:
            return int(osvi.dwMajorVersion), int(osvi.dwMinorVersion), int(osvi.dwBuildNumber)
    except Exception:
        pass

    # Fallbacks (may be affected by compat mode)
    try:
        winver = sys.getwindowsversion()
        return int(getattr(winver, "major", 0)), int(getattr(winver, "minor", 0)), int(getattr(winver, "build", 0))
    except Exception:
        return 0, 0, 0


def _enforce_windows_10_plus() -> bool:
    if sys.platform != "win32":
        return True

    major, minor, build = _get_real_windows_version()

    # Windows 10 RTM is build 10240; Windows 11 still reports major=10, build>=22000
    if (major < 10) or (major == 10 and build < 10240):
        msg = (
            "BioAttendance requires Windows 10 or later.\n\n"
            f"Detected Windows version: {major}.{minor} (build {build}).\n\n"
            "If you are on Windows 10/11 but seeing this message, "
            "disable Compatibility Mode for the installer/app and try again."
        )
        _show_msgbox_error("BioAttendance", msg)
        return False

    return True

def main():    
    
    # Run check BEFORE importing app packages
    # if not _enforce_windows_10_plus():
    #     return 1
    
    try:
        from package.app import run
        return run(sys.argv)
    except Exception as e:
        # Avoid hard crash with no context.
        try:
            from package.utils.logger import Logger
            Logger.initialize(log_file='app.log')
            Logger.error(f"Fatal startup error: {e}")
        except Exception:
            try:
                with open(DATA_DIR / "fatal_startup_error.txt", "a", encoding="utf-8") as f:
                    f.write(f"Fatal startup error: {e}\n")
            except Exception:
                print(f"Fatal startup error: {e}")
        return 1


if __name__ == '__main__':
    raise SystemExit(main())