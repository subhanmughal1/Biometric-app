import sys
from pathlib import Path


def app_root_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[2]


def resource_path(*parts: str) -> str:
    return str(app_root_dir().joinpath(*parts))
