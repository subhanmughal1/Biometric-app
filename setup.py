"""
A simple setup script to create an executable using PyQt6. This also
demonstrates how to use excludes to get minimal package size.
test_pyqt6.py is a very simple type of PyQt6 application.
Run the build process by running the command 'python setup.py build'
If everything works well you should find a subdirectory in the build
subdirectory that contains the files needed to run the application.

Commands
python setup.py build
or
python setup.py bdist_msi
"""
from __future__ import annotations

import sys,os
from pathlib import Path
from cx_Freeze import Executable, setup

appName = 'Biometric Attendance'
appTargetName = 'BioAttendance'
appShortDescription = "Biometric Attendance Gateway"
icon = os.path.join(Path(__file__).parent.resolve(),'resources','images','logo.ico')
version = "3.0.0"
upgradeCode = "{D59C7A64-18B3-2A56-A7A8-98CC34BA45BB}"
# Add author and author_email fields
author = "Mozzine Technologies"
author_email = "info@mozzine.com"
# do not edit below this line
# /////////////////////////////////////////////////////////////////////////////////////////////////////
# /////////////////////////////////////////////////////////////////////////////////////////////////////
# /////////////////////////////////////////////////////////////////////////////////////////////////////
# Include Python DLLs manually
python_dll_path = os.path.join(os.path.dirname(sys.executable), "python312.dll")
python_dll_path_versioned = os.path.join(os.path.dirname(sys.executable), f"python{sys.version_info.major}{sys.version_info.minor}.dll")

# base="Win32GUI" should be used only for Windows GUI app
# base = "Win32GUI" if sys.platform == "win32" else None
base = "Win32GUI"
try:
    from cx_Freeze.hooks import get_qt_plugins_paths
except ImportError:
    get_qt_plugins_paths = None

include_files = [
    ("resources","resources"),
    python_dll_path, 
    python_dll_path_versioned
]
if get_qt_plugins_paths:
    # Inclusion of extra plugins (since cx_Freeze 6.8b2)
    # cx_Freeze imports automatically the following plugins depending of the
    # use of some modules:
    # imageformats, platforms, platformthemes, styles - QtGui
    # mediaservice - QtMultimedia
    # printsupport - QtPrintSupport
    for plugin_name in (
        # "accessible",
        # "iconengines",
        # "platforminputcontexts",
        # "xcbglintegrations",
        # "egldeviceintegrations",
        "wayland-decoration-client",
        "wayland-graphics-integration-client",
        # "wayland-graphics-integration-server",
        "wayland-shell-integration",
    ):
        include_files += get_qt_plugins_paths("PyQt6", plugin_name)


build_exe_options = {
    "optimize": 2,
    "bin_excludes": ["libqpdf.so", "libqpdf.dylib"],      
    "packages": ["os","dotmap","PyQt6"],
    "excludes": ["tkinter",],# exclude packages that are not really needed
    "include_files": include_files,
    "zip_include_packages": ["PyQt6"],
    "include_msvcr": True,
}

directory_table = [
    ("ProgramMenuFolder", "TARGETDIR", "."),
    ("MyProgramMenu", "ProgramMenuFolder", "MYPROG~1|My Program"),
]

msi_data = {
    "Directory": directory_table,
    # "LaunchCondition": [
    #     (
    #         "(VersionNT >= 1000) OR (VersionNT64 >= 1000)",
    #         "BioAttendance requires Windows 10 or later.",
    #     ),
    # ],
    "ProgId": [
        ("Prog.Id", None, None, appShortDescription, "IconId", None),
    ],
    "Icon": [
        ("IconId", icon),
    ],
}

bdist_msi_options = {
    "add_to_path": True,
    "data": msi_data,
    # "environment_variables": [
    #     ("E_MYAPP_VAR", "=-*MYAPP_VAR", "1", "TARGETDIR")
    # ],
    "upgrade_code": upgradeCode,
    "initial_target_dir":"[ProgramFilesFolder]BioAttendance",
    "target_name":"BioAttendance",
    "install_icon": icon
}

executables = [
    Executable(
        "main.py", 
        base=base,
        icon=icon,
        target_name=appTargetName,
        shortcut_name=appTargetName,
        shortcut_dir="MyProgramMenu",
        copyright="Copyright (C) 2026 Mozzine Technologies(R)",
        uac_admin=True,
    )
]

setup(
    name=appName,
    version=version,
    description=appShortDescription,
    author=author,  
    author_email=author_email, 
    executables=executables,
    options={
        "build_exe": build_exe_options,
        "bdist_msi": bdist_msi_options,
    },
)