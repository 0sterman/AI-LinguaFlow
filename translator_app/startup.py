from __future__ import annotations

import os
import sys
from pathlib import Path


APP_SHORTCUT_NAME = "WindowsTranslator.url"


def startup_shortcut_path() -> Path:
    startup = Path(os.environ["APPDATA"]) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
    return startup / APP_SHORTCUT_NAME


def current_launch_target() -> str:
    if getattr(sys, "frozen", False):
        return sys.executable
    return str(Path(__file__).resolve().parents[1] / "run_translator.bat")


def set_start_with_windows(enabled: bool) -> None:
    shortcut = startup_shortcut_path()
    if enabled:
        shortcut.parent.mkdir(parents=True, exist_ok=True)
        target = current_launch_target()
        shortcut.write_text(
            "[InternetShortcut]\n"
            f"URL=file:///{target.replace(os.sep, '/')}\n",
            encoding="utf-8",
        )
    elif shortcut.exists():
        shortcut.unlink()


def is_start_with_windows_enabled() -> bool:
    return startup_shortcut_path().exists()
