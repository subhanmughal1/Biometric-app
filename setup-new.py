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

import sys
import os
from pathlib import Path
from cx_Freeze import Executable, setup

appName = 'Biometric Attendance'
appTargetName = 'BioAttendance.exe'
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
base = "Win32GUI" if sys.platform == "win32" else None

# -----------------------
# Helpers
# -----------------------
def add_if_exists(files_list, path, target=None):
    if path and os.path.exists(path):
        files_list.append((path, target) if target else path)


# -----------------------
# Include files
# -----------------------
include_files = [
    ("resources", "resources"),
]

# Include the correct python DLL (versioned)
python_dir = os.path.dirname(sys.executable)
python_dll_versioned = os.path.join(
    python_dir, f"python{sys.version_info.major}{sys.version_info.minor}.dll"
)
add_if_exists(include_files, python_dll_versioned)


# -----------------------
# Qt Plugins (Windows)
# -----------------------
try:
    from cx_Freeze.hooks import get_qt_plugins_paths
except Exception:
    get_qt_plugins_paths = None

if get_qt_plugins_paths and sys.platform == "win32":
    for plugin_folder in ("platforms", "styles", "imageformats", "platformthemes"):
        for item in get_qt_plugins_paths("PyQt6", plugin_folder):
            include_files.append(item)


# -----------------------
# Build options
# -----------------------
build_exe_options = {
    "optimize": 2,
    "include_msvcr": True,
    "include_files": include_files,

    # IMPORTANT: Include your own packages here (example: "package")
    "packages": [
        "dotmap",
        "PyQt6",
        "package",  # <-- change this to your actual root package name
    ],

    # If you have modules loaded dynamically, list them here
    "includes": [
        "encodings",
    ],

    "excludes": [
        "tkinter",
        "unittest",
        "pydoc",
    ],

    # Keep PyQt6 unzipped (most stable)
    "zip_include_packages": ["*"],
    "zip_exclude_packages": ["PyQt6"],
}


# -----------------------
# MSI options
# -----------------------
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
    "add_to_path": False,  # recommended for GUI apps
    "data": msi_data,
    "upgrade_code": upgradeCode,
    "initial_target_dir": "[ProgramFilesFolder]BioAttendance",
    "target_name": "BioAttendance",
    "install_icon": icon,
}


executables = [
    Executable(
        "main.py",
        base=base,
        icon=icon,
        target_name=appTargetName,
        shortcut_name="BioAttendance",
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