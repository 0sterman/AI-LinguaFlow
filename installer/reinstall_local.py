"""Reinstall the locally built application into the registered Windows location."""

from __future__ import annotations

import argparse
import ctypes
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from installer import installer_app


DEFAULT_SOURCE = PROJECT_ROOT / "dist" / installer_app.APP_NAME
DEFAULT_STATUS = Path(tempfile.gettempdir()) / "linguapopup-local-reinstall.json"


def main() -> int:
    parser = argparse.ArgumentParser(description="Reinstall the local LinguaPopUp AI build.")
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--status", type=Path, default=DEFAULT_STATUS)
    parser.add_argument("--elevated", action="store_true")
    args = parser.parse_args()

    if not args.elevated or not is_administrator():
        return relaunch_elevated(args.source, args.status)

    try:
        reinstall(args.source.resolve())
    except Exception as exc:  # noqa: BLE001 - report an install failure to the caller.
        write_status(args.status, ok=False, message=str(exc))
        return 1

    write_status(args.status, ok=True, message="Local installation completed.")
    return 0


def reinstall(source_root: Path) -> None:
    source_exe = source_root / installer_app.APP_EXE
    source_uninstaller = source_root / installer_app.UNINSTALL_EXE
    if not source_exe.exists():
        raise FileNotFoundError(f"Local build is incomplete: {source_root}")

    install_root = installer_app.find_existing_install_root(
        Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / installer_app.APP_NAME
    )
    if install_root is None:
        install_root = Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / installer_app.APP_NAME
    install_root = install_root.resolve()

    if source_root == install_root or install_root in source_root.parents:
        raise ValueError("The local build source must not be inside the installation folder.")

    preserved_uninstaller: Path | None = None
    if not source_uninstaller.exists():
        installed_uninstaller = install_root / installer_app.UNINSTALL_EXE
        if not installed_uninstaller.exists():
            raise FileNotFoundError("No uninstaller is available for the refreshed installation.")
        preserved_uninstaller = Path(tempfile.mkdtemp(prefix="LinguaPopUpAIUninstall_")) / installer_app.UNINSTALL_EXE
        shutil.copy2(installed_uninstaller, preserved_uninstaller)

    try:
        subprocess.run(
            ["taskkill", "/IM", "LinguaPopUp AI Setup.exe", "/F"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        installer_app.stop_running_app()
        installer_app.prepare_install_root(install_root)
        shutil.copytree(source_root, install_root)
        if preserved_uninstaller is not None:
            shutil.copy2(preserved_uninstaller, install_root / installer_app.UNINSTALL_EXE)
        (install_root / installer_app.MARKER_FILE).write_text(installer_app.APP_NAME, encoding="utf-8")

        target_exe = install_root / installer_app.APP_EXE
        uninstall_exe = install_root / installer_app.UNINSTALL_EXE
        icon = install_root / "_internal" / "assets" / "app_icon.ico"
        installer_app.register_uninstall_entry(install_root, target_exe, uninstall_exe, icon if icon.exists() else target_exe)
        installer_app.write_shortcuts(
            target_exe,
            icon if icon.exists() else target_exe,
            installer_app.InstallOptions(
                install_root=install_root,
                desktop_shortcut=True,
                start_menu_shortcut=True,
                launch_after_install=False,
            ),
        )
        subprocess.Popen([str(target_exe)], cwd=str(install_root))
    finally:
        if preserved_uninstaller is not None:
            shutil.rmtree(preserved_uninstaller.parent, ignore_errors=True)


def relaunch_elevated(source: Path, status: Path) -> int:
    write_status(status, ok=False, message="Waiting for administrator approval.")
    arguments = f'"{Path(__file__).resolve()}" --source "{source}" --status "{status}" --elevated'
    result = ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, arguments, str(PROJECT_ROOT), 1)
    if result <= 32:
        write_status(status, ok=False, message=f"Windows did not start elevated Python (code {result}).")
        return 1
    return 0


def is_administrator() -> bool:
    return bool(ctypes.windll.shell32.IsUserAnAdmin())


def write_status(path: Path, *, ok: bool, message: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"ok": ok, "message": message}, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
