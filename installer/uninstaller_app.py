from __future__ import annotations

import ctypes
import os
import subprocess
import sys
import tempfile
import winreg
from pathlib import Path
from tkinter import DoubleVar, StringVar, Tk, messagebox, ttk


APP_NAME = "LinguaFlow AI"
APP_VERSION = "1.0.8"
APP_EXE = "LinguaFlow AI.exe"
WINDOW_TITLE = "LinguaFlow AI Uninstall"
UNINSTALL_KEY = r"Software\Microsoft\Windows\CurrentVersion\Uninstall\LinguaFlow AI"
SHORTCUT_NAMES = ("LinguaFlow AI Translator.lnk", "LinguaFlow AI Translator.url")


class UninstallerWindow:
    def __init__(self) -> None:
        configure_process_dpi_awareness()
        self.root = Tk()
        self.root.title(WINDOW_TITLE)
        self.root.geometry("560x280")
        self.root.minsize(560, 280)
        self.root.resizable(False, False)
        self._apply_window_icon()
        self.status = StringVar(value="Ready to uninstall")
        self.progress_value = DoubleVar(value=0)

        self.install_root = Path(sys.executable).resolve().parent
        frame = ttk.Frame(self.root, padding=24)
        frame.pack(fill="both", expand=True)

        ttk.Label(frame, text="Uninstall LinguaFlow AI", font=("Segoe UI", 18, "bold")).pack(anchor="w")
        ttk.Label(frame, text=f"Release v{APP_VERSION}", foreground="#246b92").pack(anchor="w", pady=(2, 0))
        ttk.Label(
            frame,
            text=(
                "This will remove LinguaFlow AI from this computer, including Desktop and Start menu shortcuts. "
                "Your local settings and translation history are kept unless you delete them manually."
            ),
            wraplength=500,
            justify="left",
        ).pack(anchor="w", pady=(16, 0))
        ttk.Label(frame, text=f"Installed location: {self.install_root}", wraplength=500, justify="left").pack(
            anchor="w",
            pady=(14, 0),
        )
        ttk.Progressbar(frame, mode="determinate", maximum=100, variable=self.progress_value).pack(
            fill="x",
            pady=(18, 0),
        )
        ttk.Label(frame, textvariable=self.status).pack(anchor="w", pady=(6, 0))

        button_row = ttk.Frame(frame)
        button_row.pack(fill="x", side="bottom", pady=(22, 0))
        self.cancel_button = ttk.Button(button_row, text="Cancel", command=self.root.destroy)
        self.cancel_button.pack(side="right", padx=(8, 0))
        self.uninstall_button = ttk.Button(button_row, text="Uninstall", command=self._confirm_uninstall)
        self.uninstall_button.pack(side="right")

    def run(self) -> int:
        self.root.mainloop()
        return 0

    def _apply_window_icon(self) -> None:
        icon_path = self.install_root_icon()
        if icon_path.exists():
            try:
                self.root.iconbitmap(str(icon_path))
            except Exception:
                pass

    def install_root_icon(self) -> Path:
        return Path(sys.executable).resolve().parent / "_internal" / "assets" / "app_icon.ico"

    def _confirm_uninstall(self) -> None:
        if not messagebox.askyesno(WINDOW_TITLE, "Uninstall LinguaFlow AI now?"):
            return
        self.cancel_button.configure(state="disabled")
        self.uninstall_button.configure(state="disabled")
        try:
            uninstall(self.install_root, self._apply_progress)
        except Exception as exc:  # noqa: BLE001 - user-facing uninstaller.
            self.cancel_button.configure(state="normal")
            self.uninstall_button.configure(state="normal")
            messagebox.showerror(WINDOW_TITLE, f"Could not uninstall LinguaFlow AI.\n\n{exc}")
            return
        self.progress_value.set(100)
        self.status.set("Completed")
        messagebox.showinfo(WINDOW_TITLE, "LinguaFlow AI has been uninstalled.")
        self.root.destroy()

    def _apply_progress(self, value: int, status: str) -> None:
        self.progress_value.set(value)
        self.status.set(status)
        self.root.update_idletasks()


def uninstall(install_root: Path, progress: object | None = None) -> None:
    _report(progress, 15, "Closing running app...")
    stop_running_app()
    _report(progress, 35, "Removing shortcuts...")
    remove_shortcuts()
    _report(progress, 58, "Removing Windows uninstall entry...")
    remove_registry_entries()
    _report(progress, 82, "Scheduling application folder removal...")
    schedule_install_folder_removal(install_root)
    _report(progress, 100, "Completed")


def _report(progress: object | None, value: int, status: str) -> None:
    if callable(progress):
        progress(value, status)


def stop_running_app() -> None:
    current_pid = os.getpid()
    command = (
        f"Get-Process -Name '{Path(APP_EXE).stem}' -ErrorAction SilentlyContinue | "
        f"Where-Object {{ $_.Id -ne {current_pid} }} | Stop-Process -Force"
    )
    subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", command],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        startupinfo=hidden_startupinfo(),
        creationflags=hidden_creationflags(),
        check=False,
    )


def remove_shortcuts() -> None:
    locations = [
        Path(os.environ.get("PUBLIC", str(Path.home()))) / "Desktop",
        Path.home() / "Desktop",
        Path(os.environ.get("ProgramData", os.environ.get("APPDATA", ""))) / "Microsoft" / "Windows" / "Start Menu" / "Programs",
        Path(os.environ.get("APPDATA", "")) / "Microsoft" / "Windows" / "Start Menu" / "Programs",
        Path(os.environ.get("APPDATA", "")) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup",
    ]
    for location in locations:
        for shortcut_name in SHORTCUT_NAMES:
            shortcut = location / shortcut_name
            try:
                if shortcut.exists():
                    shortcut.unlink()
            except OSError:
                pass


def remove_registry_entries() -> None:
    for root in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
        try:
            winreg.DeleteKey(root, UNINSTALL_KEY)
        except OSError:
            pass


def schedule_install_folder_removal(install_root: Path) -> None:
    script_path = Path(tempfile.gettempdir()) / "uninstall_linguaflow_cleanup.cmd"
    script_path.write_text(
        "@echo off\n"
        "timeout /t 2 /nobreak >nul\n"
        f'rmdir /s /q "{install_root}"\n'
        f'del "%~f0"\n',
        encoding="utf-8",
    )
    subprocess.Popen(
        [os.environ.get("ComSpec", "cmd.exe"), "/c", str(script_path)],
        cwd=str(Path(tempfile.gettempdir())),
        startupinfo=hidden_startupinfo(),
        creationflags=hidden_creationflags(),
    )


def hidden_startupinfo() -> subprocess.STARTUPINFO | None:
    if sys.platform != "win32":
        return None
    startupinfo = subprocess.STARTUPINFO()
    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    startupinfo.wShowWindow = 0
    return startupinfo


def hidden_creationflags() -> int:
    return subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0


def show_message(title: str, text: str, icon_error: bool = False) -> None:
    flags = 0x00000010 if icon_error else 0x00000040
    ctypes.windll.user32.MessageBoxW(None, text, title, flags)


def configure_process_dpi_awareness() -> None:
    if sys.platform != "win32":
        return
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass


def main() -> int:
    try:
        configure_process_dpi_awareness()
        if "--quiet" in sys.argv:
            uninstall(Path(sys.executable).resolve().parent)
            return 0
        return UninstallerWindow().run()
    except Exception as exc:  # noqa: BLE001 - last-resort UI fallback.
        show_message(WINDOW_TITLE, f"Could not uninstall LinguaFlow AI.\n\n{exc}", icon_error=True)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
