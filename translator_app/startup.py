from __future__ import annotations

import os
import sys
import ctypes
import subprocess
import uuid
from pathlib import Path


APP_SHORTCUT_NAME = "LinguaFlow AI Translator.lnk"
URL_APP_SHORTCUT_NAME = "LinguaFlow AI Translator.url"
LEGACY_SHORTCUT_NAME = "WindowsTranslator.url"
OLD_APP_SHORTCUT_NAME = "AI-LinguaFlow.url"
PREVIOUS_APP_SHORTCUT_NAME = "AI LinguaFlow.url"
MACOS_BUNDLE_ID = "com.oster.linguaflow"
MACOS_LAUNCH_AGENT_NAME = f"{MACOS_BUNDLE_ID}.plist"


def startup_shortcut_path() -> Path:
    if sys.platform == "darwin":
        return Path.home() / "Library" / "LaunchAgents" / MACOS_LAUNCH_AGENT_NAME
    startup = Path(os.environ["APPDATA"]) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
    return startup / APP_SHORTCUT_NAME


def desktop_shortcut_path() -> Path:
    if sys.platform == "darwin":
        return desktop_dir() / "LinguaFlow AI.app"
    return desktop_dir() / APP_SHORTCUT_NAME


def desktop_dir() -> Path:
    known_folder = _known_desktop_path()
    if known_folder is not None:
        return known_folder
    return Path.home() / "Desktop"


def current_launch_target() -> str:
    if getattr(sys, "frozen", False):
        return sys.executable
    if sys.platform == "darwin":
        return str(Path(__file__).resolve().parents[1] / "run_macos.sh")
    return str(Path(__file__).resolve().parents[1] / "run_translator.bat")


def current_icon_target() -> str:
    if getattr(sys, "frozen", False):
        app_root = Path(sys.executable).resolve().parent
        installed_icon = app_root / "_internal" / "assets" / "app_icon.ico"
        if installed_icon.exists():
            return str(installed_icon)
        return sys.executable
    return str(Path(__file__).resolve().parents[1] / "assets" / "app_icon.ico")


def set_start_with_windows(enabled: bool) -> None:
    shortcut = startup_shortcut_path()
    if sys.platform == "darwin":
        if enabled:
            shortcut.parent.mkdir(parents=True, exist_ok=True)
            shortcut.write_text(_macos_launch_agent_plist(current_launch_target()), encoding="utf-8")
        elif shortcut.exists():
            shortcut.unlink()
        return
    if enabled:
        shortcut.parent.mkdir(parents=True, exist_ok=True)
        _write_shortcut(shortcut, current_launch_target(), current_icon_target())
    elif shortcut.exists():
        shortcut.unlink()
    if not enabled:
        for stale_shortcut in _stale_shortcut_paths(shortcut):
            if stale_shortcut.exists():
                stale_shortcut.unlink()


def is_start_with_windows_enabled() -> bool:
    return startup_shortcut_path().exists()


def set_desktop_shortcut(enabled: bool) -> None:
    shortcut = desktop_shortcut_path()
    if sys.platform == "darwin":
        if enabled:
            shortcut.parent.mkdir(parents=True, exist_ok=True)
            target = _macos_app_bundle_path()
            if target is None:
                return
            if shortcut.exists() or shortcut.is_symlink():
                shortcut.unlink()
            shortcut.symlink_to(target, target_is_directory=True)
        elif shortcut.exists() or shortcut.is_symlink():
            shortcut.unlink()
        return
    if enabled:
        shortcut.parent.mkdir(parents=True, exist_ok=True)
        created_shortcut = _write_shortcut(shortcut, current_launch_target(), current_icon_target())
        stale_shortcuts = _stale_desktop_shortcut_paths(created_shortcut)
    else:
        if shortcut.exists():
            shortcut.unlink()
        stale_shortcuts = _stale_desktop_shortcut_paths(shortcut)
    for stale_shortcut in stale_shortcuts:
        if stale_shortcut.exists():
            stale_shortcut.unlink()


def is_desktop_shortcut_enabled() -> bool:
    return desktop_shortcut_path().exists()


def ensure_desktop_shortcut() -> None:
    set_desktop_shortcut(True)


def _macos_app_bundle_path() -> Path | None:
    if getattr(sys, "frozen", False):
        executable = Path(sys.executable).resolve()
        for parent in executable.parents:
            if parent.suffix == ".app":
                return parent
    return None


def _macos_launch_agent_plist(target: str) -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" '
        '"http://www.apple.com/DTDs/PropertyList-1.0.dtd">\n'
        '<plist version="1.0">\n'
        '<dict>\n'
        f'  <key>Label</key><string>{MACOS_BUNDLE_ID}</string>\n'
        "  <key>ProgramArguments</key>\n"
        "  <array>\n"
        f"    <string>{target}</string>\n"
        "  </array>\n"
        "  <key>RunAtLoad</key><true/>\n"
        "  <key>KeepAlive</key><false/>\n"
        "</dict>\n"
        "</plist>\n"
    )


def _write_url_shortcut(path: Path, target: str, icon: str) -> None:
    path.write_text(
        "[InternetShortcut]\n"
        f"URL=file:///{target.replace(os.sep, '/')}\n"
        f"IconFile={icon}\n"
        "IconIndex=0\n",
        encoding="utf-8",
    )


def _write_shortcut(path: Path, target: str, icon: str) -> Path:
    if sys.platform == "win32" and path.suffix.lower() == ".lnk":
        try:
            _write_lnk_shortcut(path, target, icon)
            return path
        except Exception:
            path = path.with_suffix(".url")
    _write_url_shortcut(path, target, icon)
    return path


def _write_lnk_shortcut(path: Path, target: str, icon: str) -> None:
    script = (
        "$shortcutPath=$args[0];"
        "$targetPath=$args[1];"
        "$iconPath=$args[2];"
        "$shell=New-Object -ComObject WScript.Shell;"
        "$shortcut=$shell.CreateShortcut($shortcutPath);"
        "$shortcut.TargetPath=$targetPath;"
        "$shortcut.WorkingDirectory=Split-Path -Parent $targetPath;"
        "$shortcut.IconLocation=$iconPath + ',0';"
        "$shortcut.Save();"
    )
    subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script, str(path), target, icon],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        startupinfo=_hidden_startupinfo(),
        creationflags=_hidden_creationflags(),
        check=True,
    )


def _hidden_startupinfo() -> subprocess.STARTUPINFO | None:
    if sys.platform != "win32":
        return None
    startupinfo = subprocess.STARTUPINFO()
    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    startupinfo.wShowWindow = 0
    return startupinfo


def _hidden_creationflags() -> int:
    return subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0


def _stale_shortcut_paths(active_shortcut: Path) -> list[Path]:
    candidates = [
        active_shortcut.with_name(URL_APP_SHORTCUT_NAME),
        active_shortcut.with_name(OLD_APP_SHORTCUT_NAME),
        active_shortcut.with_name(PREVIOUS_APP_SHORTCUT_NAME),
        active_shortcut.with_name(LEGACY_SHORTCUT_NAME),
    ]
    return [path for path in candidates if path != active_shortcut]


def _stale_desktop_shortcut_paths(active_shortcut: Path) -> list[Path]:
    candidates = [
        *_stale_shortcut_paths(active_shortcut),
        active_shortcut.with_name(OLD_APP_SHORTCUT_NAME),
        active_shortcut.with_name(PREVIOUS_APP_SHORTCUT_NAME),
        active_shortcut.with_name(LEGACY_SHORTCUT_NAME),
        Path.home() / "Desktop" / APP_SHORTCUT_NAME,
        Path.home() / "Desktop" / URL_APP_SHORTCUT_NAME,
        Path.home() / "Desktop" / OLD_APP_SHORTCUT_NAME,
        Path.home() / "Desktop" / PREVIOUS_APP_SHORTCUT_NAME,
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
