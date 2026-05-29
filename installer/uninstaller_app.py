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
        self.install_root = determine_install_root()
        self.root = Tk()
        self.root.title(WINDOW_TITLE)
        self.root.geometry("660x460")
        self.root.minsize(660, 460)
        self.root.resizable(False, False)
        self._apply_window_icon()
        self.status = StringVar(value="Ready to uninstall")
        self.progress_value = DoubleVar(value=0)

        frame = ttk.Frame(self.root, padding=24)
        frame.pack(fill="both", expand=True)
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(0, weight=1)

        content = ttk.Frame(frame)
        content.grid(row=0, column=0, sticky="nsew")
        content.columnconfigure(0, weight=1)

        ttk.Label(content, text="Uninstall LinguaFlow AI", font=("Segoe UI", 18, "bold")).grid(
            row=0,
            column=0,
            sticky="w",
        )
        ttk.Label(content, text=f"Release v{APP_VERSION}", foreground="#246b92").grid(
            row=1,
            column=0,
            sticky="w",
            pady=(2, 0),
        )
        ttk.Label(
            content,
            text=(
                "This will remove LinguaFlow AI from this computer, including Desktop and Start menu shortcuts. "
                "Your local settings and translation history are kept unless you delete them manually."
            ),
            wraplength=580,
            justify="left",
        ).grid(row=2, column=0, sticky="w", pady=(18, 0))
        ttk.Label(
            content,
            text=f"Installed location: {self.install_root}",
            wraplength=580,
            justify="left",
        ).grid(
            row=3,
            column=0,
            sticky="w",
            pady=(14, 0),
        )
        ttk.Progressbar(content, mode="determinate", maximum=100, variable=self.progress_value).grid(
            row=4,
            column=0,
            sticky="ew",
            pady=(18, 0),
        )
        ttk.Label(content, textvariable=self.status).grid(row=5, column=0, sticky="w", pady=(8, 0))

        button_row = ttk.Frame(frame)
        button_row.grid(row=1, column=0, sticky="ew", pady=(22, 0))
        button_row.columnconfigure(0, weight=1)
        self.cancel_button = ttk.Button(button_row, text="Cancel", command=self.root.destroy)
        self.cancel_button.grid(row=0, column=2, padx=(8, 0))
        self.uninstall_button = ttk.Button(button_row, text="Uninstall", command=self._confirm_uninstall)
        self.uninstall_button.grid(row=0, column=1)

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
        bundled_icon = Path(sys.executable).resolve().parent / "_internal" / "assets" / "app_icon.ico"
        if bundled_icon.exists():
            return bundled_icon
        return self.install_root / "_internal" / "assets" / "app_icon.ico"

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


def determine_install_root() -> Path:
    args = sys.argv[1:]
    for index, arg in enumerate(args):
        if arg == "--install-root" and index + 1 < len(args):
            return Path(args[index + 1]).expanduser().resolve()
        if arg.startswith("--install-root="):
            return Path(arg.split("=", 1)[1]).expanduser().resolve()

    registered_root = read_registered_install_location()
    if registered_root is not None:
        return registered_root
    return Path(sys.executable).resolve().parent


def read_registered_install_location() -> Path | None:
    if sys.platform != "win32":
        return None
    access_masks = (winreg.KEY_READ | getattr(winreg, "KEY_WOW64_64KEY", 0), winreg.KEY_READ)
    for root in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
        for access in access_masks:
            try:
                with winreg.OpenKey(root, UNINSTALL_KEY, 0, access) as key:
                    value, _ = winreg.QueryValueEx(key, "InstallLocation")
            except OSError:
                continue
            path = Path(str(value)).expanduser()
            if path.exists():
                return path.resolve()
    return None


def is_user_admin() -> bool:
    if sys.platform != "win32":
        return True
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def needs_admin_for_path(path: Path) -> bool:
    if sys.platform != "win32":
        return False
    program_dirs = [
        os.environ.get("ProgramFiles"),
        os.environ.get("ProgramFiles(x86)"),
    ]
    path_text = str(path.resolve()).casefold()
    for program_dir in program_dirs:
        if program_dir and path_text.startswith(str(Path(program_dir).resolve()).casefold()):
            return True
    return False


def relaunch_elevated(install_root: Path, quiet: bool) -> bool:
    if sys.platform != "win32" or is_user_admin() or not needs_admin_for_path(install_root):
        return False
    params = ["--install-root", str(install_root)]
    if quiet:
        params.append("--quiet")
    arguments = subprocess.list2cmdline(params)
    result = ctypes.windll.shell32.ShellExecuteW(
        None,
        "runas",
        sys.executable,
        arguments,
        str(Path(sys.executable).resolve().parent),
        1,
    )
    return int(result) > 32


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
        install_root = determine_install_root()
        quiet = "--quiet" in sys.argv
        if relaunch_elevated(install_root, quiet):
            return 0
        if quiet:
            uninstall(install_root)
            return 0
        return UninstallerWindow().run()
    except Exception as exc:  # noqa: BLE001 - last-resort UI fallback.
        show_message(WINDOW_TITLE, f"Could not uninstall LinguaFlow AI.\n\n{exc}", icon_error=True)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
