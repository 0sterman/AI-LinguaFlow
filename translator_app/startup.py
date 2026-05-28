from __future__ import annotations

import os
import sys
import ctypes
import uuid
from pathlib import Path


APP_SHORTCUT_NAME = "AI-LinguaFlow.url"
LEGACY_SHORTCUT_NAME = "WindowsTranslator.url"


def startup_shortcut_path() -> Path:
    startup = Path(os.environ["APPDATA"]) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
    return startup / APP_SHORTCUT_NAME


def desktop_shortcut_path() -> Path:
    return desktop_dir() / APP_SHORTCUT_NAME


def desktop_dir() -> Path:
    known_folder = _known_desktop_path()
    if known_folder is not None:
        return known_folder
    return Path.home() / "Desktop"


def current_launch_target() -> str:
    if getattr(sys, "frozen", False):
        return sys.executable
    return str(Path(__file__).resolve().parents[1] / "run_translator.bat")


def current_icon_target() -> str:
    if getattr(sys, "frozen", False):
        return sys.executable
    return str(Path(__file__).resolve().parents[1] / "assets" / "app_icon.ico")


def set_start_with_windows(enabled: bool) -> None:
    shortcut = startup_shortcut_path()
    if enabled:
        shortcut.parent.mkdir(parents=True, exist_ok=True)
        _write_url_shortcut(shortcut, current_launch_target(), current_icon_target())
    elif shortcut.exists():
        shortcut.unlink()
    legacy_shortcut = shortcut.with_name(LEGACY_SHORTCUT_NAME)
    if legacy_shortcut.exists() and not enabled:
        legacy_shortcut.unlink()


def is_start_with_windows_enabled() -> bool:
    return startup_shortcut_path().exists()


def set_desktop_shortcut(enabled: bool) -> None:
    shortcut = desktop_shortcut_path()
    if enabled:
        shortcut.parent.mkdir(parents=True, exist_ok=True)
        _write_url_shortcut(shortcut, current_launch_target(), current_icon_target())
    elif shortcut.exists():
        shortcut.unlink()
    legacy_shortcut = shortcut.with_name(LEGACY_SHORTCUT_NAME)
    if legacy_shortcut.exists() and not enabled:
        legacy_shortcut.unlink()
    for stale_shortcut in _stale_desktop_shortcut_paths(shortcut):
        if stale_shortcut.exists():
            stale_shortcut.unlink()


def is_desktop_shortcut_enabled() -> bool:
    return desktop_shortcut_path().exists()


def ensure_desktop_shortcut() -> None:
    if not is_desktop_shortcut_enabled():
        set_desktop_shortcut(True)


def _write_url_shortcut(path: Path, target: str, icon: str) -> None:
    path.write_text(
        "[InternetShortcut]\n"
        f"URL=file:///{target.replace(os.sep, '/')}\n"
        f"IconFile={icon}\n"
        "IconIndex=0\n",
        encoding="utf-8",
    )


def _stale_desktop_shortcut_paths(active_shortcut: Path) -> list[Path]:
    candidates = [
        Path.home() / "Desktop" / APP_SHORTCUT_NAME,
        Path.home() / "Desktop" / LEGACY_SHORTCUT_NAME,
    ]
    return [path for path in candidates if path != active_shortcut]


def _known_desktop_path() -> Path | None:
    if sys.platform != "win32":
        return None

    folder_id = uuid.UUID("B4BFCC3A-DB2C-424C-B029-7FE99A87C641")
    path_pointer = ctypes.c_wchar_p()
    result = ctypes.windll.shell32.SHGetKnownFolderPath(
        ctypes.byref(_guid_to_struct(folder_id)),
        0,
        None,
        ctypes.byref(path_pointer),
    )
    if result != 0:
        return None
    try:
        return Path(path_pointer.value)
    finally:
        ctypes.windll.ole32.CoTaskMemFree(path_pointer)


class GUID(ctypes.Structure):
    _fields_ = [
        ("Data1", ctypes.c_ulong),
        ("Data2", ctypes.c_ushort),
        ("Data3", ctypes.c_ushort),
        ("Data4", ctypes.c_ubyte * 8),
    ]


def _guid_to_struct(value: uuid.UUID) -> GUID:
    fields = value.fields
    data4 = (ctypes.c_ubyte * 8)(*value.bytes[8:])
    return GUID(fields[0], fields[1], fields[2], data4)
