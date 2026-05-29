from __future__ import annotations

import ctypes
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import winreg
import zipfile
from dataclasses import dataclass
from pathlib import Path
from tkinter import BooleanVar, StringVar, Tk, filedialog, messagebox, ttk


APP_NAME = "LinguaFlow AI"
APP_VERSION = "0.1.0"
APP_PUBLISHER = "LinguaFlow AI"
APP_EXE = "LinguaFlow AI.exe"
SHORTCUT_NAME = "LinguaFlow AI Translator.url"
PAYLOAD_ZIP = "LinguaFlowAI_payload.zip"
MARKER_FILE = ".linguaflow-install"
UNINSTALL_KEY = r"Software\Microsoft\Windows\CurrentVersion\Uninstall\LinguaFlow AI"


@dataclass(frozen=True)
class InstallOptions:
    install_root: Path
    desktop_shortcut: bool
    start_menu_shortcut: bool
    launch_after_install: bool


class InstallerWizard:
    def __init__(self) -> None:
        self.root = Tk()
        self.root.title("LinguaFlow AI Setup")
        self.root.geometry("680x430")
        self.root.minsize(640, 410)
        self.root.resizable(False, False)

        default_dir = Path(os.environ["LOCALAPPDATA"]) / "Programs" / APP_NAME
        self.install_dir = StringVar(value=str(default_dir))
        self.desktop_shortcut = BooleanVar(value=True)
        self.start_menu_shortcut = BooleanVar(value=True)
        self.launch_after_install = BooleanVar(value=False)
        self.status = StringVar(value="Готово к установке")

        self._build_ui()

    def run(self) -> int:
        self.root.mainloop()
        return 0

    def _build_ui(self) -> None:
        outer = ttk.Frame(self.root, padding=22)
        outer.pack(fill="both", expand=True)

        title = ttk.Label(outer, text="Установка LinguaFlow AI", font=("Segoe UI", 18, "bold"))
        title.pack(anchor="w")

        description = ttk.Label(
            outer,
            text=(
                "LinguaFlow AI - быстрый Windows-переводчик для выделенного текста через Ctrl+C+C "
                "и обычного ручного перевода. Программа хранит историю локально и работает через "
                "выбранный вами AI-провайдер."
            ),
            wraplength=610,
            justify="left",
        )
        description.pack(anchor="w", pady=(8, 18))

        path_label = ttk.Label(outer, text="Папка установки")
        path_label.pack(anchor="w")

        path_row = ttk.Frame(outer)
        path_row.pack(fill="x", pady=(4, 12))
        path_entry = ttk.Entry(path_row, textvariable=self.install_dir)
        path_entry.pack(side="left", fill="x", expand=True)
        browse_button = ttk.Button(path_row, text="Обзор...", command=self._choose_folder)
        browse_button.pack(side="left", padx=(8, 0))

        options_box = ttk.LabelFrame(outer, text="Параметры")
        options_box.pack(fill="x", pady=(0, 14))
        ttk.Checkbutton(options_box, text="Создать ярлык на рабочем столе", variable=self.desktop_shortcut).pack(
            anchor="w", padx=12, pady=(9, 3)
        )
        ttk.Checkbutton(options_box, text="Добавить ярлык в меню Пуск", variable=self.start_menu_shortcut).pack(
            anchor="w", padx=12, pady=3
        )
        ttk.Checkbutton(options_box, text="Запустить LinguaFlow AI после установки", variable=self.launch_after_install).pack(
            anchor="w", padx=12, pady=(3, 9)
        )

        note = ttk.Label(
            outer,
            text=(
                "После установки нужно ввести личный API-ключ в Настройки -> API. "
                "Инструкция находится в Настройки -> Основное -> Инструкция."
            ),
            wraplength=610,
            justify="left",
        )
        note.pack(anchor="w", pady=(0, 12))

        self.progress = ttk.Progressbar(outer, mode="indeterminate")
        self.progress.pack(fill="x", pady=(0, 8))
        ttk.Label(outer, textvariable=self.status).pack(anchor="w")

        buttons = ttk.Frame(outer)
        buttons.pack(fill="x", pady=(16, 0))
        ttk.Button(buttons, text="Отмена", command=self.root.destroy).pack(side="right")
        self.install_button = ttk.Button(buttons, text="Установить", command=self._start_install)
        self.install_button.pack(side="right", padx=(0, 8))

    def _choose_folder(self) -> None:
        selected = filedialog.askdirectory(
            title="Выберите папку установки",
            initialdir=str(Path(self.install_dir.get()).parent),
        )
        if selected:
            self.install_dir.set(selected)

    def _start_install(self) -> None:
        try:
            options = InstallOptions(
                install_root=Path(self.install_dir.get()).expanduser(),
                desktop_shortcut=self.desktop_shortcut.get(),
                start_menu_shortcut=self.start_menu_shortcut.get(),
                launch_after_install=self.launch_after_install.get(),
            )
            validate_install_root(options.install_root)
        except Exception as exc:  # noqa: BLE001 - user-facing validation.
            messagebox.showerror("LinguaFlow AI Setup", str(exc))
            return

        self.install_button.configure(state="disabled")
        self.progress.start(12)
        self.status.set("Устанавливаю LinguaFlow AI...")

        thread = threading.Thread(target=self._install_in_background, args=(options,), daemon=True)
        thread.start()

    def _install_in_background(self, options: InstallOptions) -> None:
        try:
            install(options)
        except Exception as exc:  # noqa: BLE001 - user-facing installer.
            self.root.after(0, lambda: self._finish_with_error(exc))
            return
        self.root.after(0, self._finish_success)

    def _finish_with_error(self, exc: Exception) -> None:
        self.progress.stop()
        self.install_button.configure(state="normal")
        self.status.set("Установка не завершена")
        messagebox.showerror("LinguaFlow AI Setup", f"Не удалось установить LinguaFlow AI.\n\n{exc}")

    def _finish_success(self) -> None:
        self.progress.stop()
        self.status.set("Установка завершена")
        messagebox.showinfo(
            "LinguaFlow AI Setup",
            "Установка LinguaFlow AI завершена.\n\n"
            "Для корректной работы необходимо ввести свой API-ключ: Настройки -> API.\n\n"
            "Ответы по работе с программой можно найти в Настройки -> Основное -> Инструкция.",
        )
        self.root.destroy()


def main() -> int:
    try:
        return InstallerWizard().run()
    except Exception as exc:  # noqa: BLE001 - last-resort UI fallback.
        show_message(
            "LinguaFlow AI Setup",
            f"Не удалось запустить установщик LinguaFlow AI.\n\n{exc}",
            icon_error=True,
        )
        return 1


def install(options: InstallOptions) -> None:
    payload = resource_path(PAYLOAD_ZIP)
    if not payload.exists():
        raise FileNotFoundError(f"Не найден установочный пакет: {payload}")

    install_root = options.install_root.resolve()
    temp_root = Path(tempfile.mkdtemp(prefix="LinguaFlowAIInstall_"))

    try:
        stop_running_app()

        with zipfile.ZipFile(payload) as archive:
            archive.extractall(temp_root)

        source_root = temp_root / APP_NAME
        source_exe = source_root / APP_EXE
        if not source_exe.exists():
            raise FileNotFoundError("В пакете нет LinguaFlow AI.exe")

        prepare_install_root(install_root)
        shutil.copytree(source_root, install_root)
        (install_root / MARKER_FILE).write_text(APP_NAME, encoding="utf-8")

        target_exe = install_root / APP_EXE
        write_uninstaller(install_root)
        register_uninstall_entry(install_root, target_exe)
        write_shortcuts(target_exe, target_exe, options)

        if options.launch_after_install:
            subprocess.Popen([str(target_exe)], cwd=str(install_root))
    finally:
        shutil.rmtree(temp_root, ignore_errors=True)


def validate_install_root(install_root: Path) -> None:
    if not str(install_root).strip():
        raise ValueError("Выберите папку установки.")

    resolved = install_root.resolve()
    if resolved.anchor and str(resolved) == resolved.anchor:
        raise ValueError("Нельзя устанавливать программу прямо в корень диска.")

    if resolved.exists() and any(resolved.iterdir()) and not (resolved / MARKER_FILE).exists():
        raise ValueError(
            "Выбранная папка уже содержит файлы другой программы или пользователя. "
            "Выберите пустую папку или прежнюю папку установки LinguaFlow AI."
        )


def prepare_install_root(install_root: Path) -> None:
    validate_install_root(install_root)
    if install_root.exists():
        shutil.rmtree(install_root)
    install_root.parent.mkdir(parents=True, exist_ok=True)


def resource_path(name: str) -> Path:
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return base / name


def stop_running_app() -> None:
    subprocess.run(
        ["taskkill", "/IM", APP_EXE, "/F"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )


def write_shortcuts(target_exe: Path, icon_path: Path, options: InstallOptions) -> None:
    if options.desktop_shortcut:
        desktop = Path(os.path.expanduser("~")) / "Desktop"
        write_url_shortcut(desktop / SHORTCUT_NAME, target_exe, icon_path)

    if options.start_menu_shortcut:
        start_menu = Path(os.environ["APPDATA"]) / "Microsoft" / "Windows" / "Start Menu" / "Programs"
        write_url_shortcut(start_menu / SHORTCUT_NAME, target_exe, icon_path)


def write_url_shortcut(path: Path, target: Path, icon: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(
            [
                "[InternetShortcut]",
                f"URL={target.resolve().as_uri()}",
                f"IconFile={icon}",
                "IconIndex=0",
            ]
        )
        + "\n",
        encoding="utf-8",
    )


def write_uninstaller(install_root: Path) -> None:
    script_path = install_root / "uninstall_linguaflow.ps1"
    lines = [
        '$ErrorActionPreference = "SilentlyContinue"',
        f'Get-Process -Name "{APP_NAME}" -ErrorAction SilentlyContinue | Stop-Process -Force',
        "$installRoot = Split-Path -Parent $MyInvocation.MyCommand.Path",
        f'Remove-Item -LiteralPath (Join-Path ([Environment]::GetFolderPath("Desktop")) "{SHORTCUT_NAME}") -Force',
        f'Remove-Item -LiteralPath (Join-Path $env:APPDATA "Microsoft\\Windows\\Start Menu\\Programs\\{SHORTCUT_NAME}") -Force',
        f'Remove-Item -LiteralPath (Join-Path $env:APPDATA "Microsoft\\Windows\\Start Menu\\Programs\\Startup\\{SHORTCUT_NAME}") -Force',
        f'Remove-Item -LiteralPath "HKCU:\\{UNINSTALL_KEY}" -Recurse -Force',
        '$deleteCommand = \'/c timeout /t 2 /nobreak >nul & rmdir /s /q "\' + $installRoot + \'"\'',
        'Start-Process -FilePath $env:ComSpec -WorkingDirectory $env:TEMP -WindowStyle Hidden -ArgumentList $deleteCommand',
    ]
    script_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def register_uninstall_entry(install_root: Path, target_exe: Path) -> None:
    uninstall_script = install_root / "uninstall_linguaflow.ps1"
    uninstall_command = (
        f'powershell.exe -NoProfile -ExecutionPolicy Bypass -File "{uninstall_script}"'
    )
    estimated_size_kb = sum(file.stat().st_size for file in install_root.rglob("*") if file.is_file()) // 1024

    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, UNINSTALL_KEY) as key:
        winreg.SetValueEx(key, "DisplayName", 0, winreg.REG_SZ, APP_NAME)
        winreg.SetValueEx(key, "DisplayVersion", 0, winreg.REG_SZ, APP_VERSION)
        winreg.SetValueEx(key, "Publisher", 0, winreg.REG_SZ, APP_PUBLISHER)
        winreg.SetValueEx(key, "InstallLocation", 0, winreg.REG_SZ, str(install_root))
        winreg.SetValueEx(key, "DisplayIcon", 0, winreg.REG_SZ, str(target_exe))
        winreg.SetValueEx(key, "UninstallString", 0, winreg.REG_SZ, uninstall_command)
        winreg.SetValueEx(key, "QuietUninstallString", 0, winreg.REG_SZ, uninstall_command)
        winreg.SetValueEx(key, "NoModify", 0, winreg.REG_DWORD, 1)
        winreg.SetValueEx(key, "NoRepair", 0, winreg.REG_DWORD, 1)
        winreg.SetValueEx(key, "EstimatedSize", 0, winreg.REG_DWORD, int(estimated_size_kb))


def show_message(title: str, text: str, icon_error: bool = False) -> None:
    flags = 0x00000010 if icon_error else 0x00000040
    ctypes.windll.user32.MessageBoxW(None, text, title, flags)


if __name__ == "__main__":
    raise SystemExit(main())
