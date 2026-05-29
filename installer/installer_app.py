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
from tkinter import BooleanVar, DoubleVar, PhotoImage, StringVar, Tk, filedialog, messagebox, ttk


APP_NAME = "LinguaFlow AI"
APP_VERSION = "1.0.7"
APP_PUBLISHER = "Roman Ostroumov / Oster"
APP_EXE = "LinguaFlow AI.exe"
UNINSTALL_EXE = "LinguaFlow AI Uninstall.exe"
WINDOW_TITLE = "LinguaFlow AI - Popup Translator - © Roman Ostroumov / Oster"
SHORTCUT_NAME = "LinguaFlow AI Translator.lnk"
URL_SHORTCUT_NAME = "LinguaFlow AI Translator.url"
PAYLOAD_ZIP = "LinguaFlowAI_payload.zip"
MARKER_FILE = ".linguaflow-install"
UNINSTALL_KEY = r"Software\Microsoft\Windows\CurrentVersion\Uninstall\LinguaFlow AI"

INSTALLER_COPY = {
    "en": {
        "language_name": "English",
        "title": "LinguaFlow AI Setup",
        "welcome_title": "Welcome to LinguaFlow AI",
        "release": "Release",
        "language": "Setup language",
        "welcome": "LinguaFlow AI is a compact Windows translator for selected text.",
        "highlight": "Select text anywhere, press Ctrl+C+C, and get a fast popup translation.",
        "details": (
            "The app also supports normal manual translation, local translation history, "
            "and your choice of OpenAI, Google Gemini, or Anthropic Claude. "
            "Default installation folder: Program Files."
        ),
        "api_note": (
            "After installation, enter your own API key in Settings -> API. "
            "Usage answers are available in Settings -> General -> Guide."
        ),
        "destination_title": "Choose installation options",
        "install_folder": "Installation folder",
        "browse": "Browse...",
        "options": "Options",
        "desktop_shortcut": "Create a desktop shortcut",
        "start_menu_shortcut": "Add a Start menu shortcut",
        "launch_after_install": "Launch LinguaFlow AI after installation",
        "ready": "Ready to install",
        "stopping": "Closing running app...",
        "extracting": "Extracting files...",
        "copying": "Copying application files...",
        "shortcuts": "Creating shortcuts...",
        "registering": "Registering Windows uninstall entry...",
        "launching": "Launching LinguaFlow AI...",
        "installing": "Installing LinguaFlow AI...",
        "failed": "Installation was not completed",
        "completed": "Installation completed",
        "success": (
            "LinguaFlow AI has been installed.\n\n"
            "For correct operation, enter your own API key: Settings -> API.\n\n"
            "Usage answers are available in Settings -> General -> Guide."
        ),
        "startup_error": "Could not start LinguaFlow AI Setup.",
        "install_error": "Could not install LinguaFlow AI.",
        "choose_folder": "Choose installation folder",
        "continue": "Continue",
        "back": "Back",
        "install": "Install",
        "cancel": "Cancel",
        "empty_folder": "Choose an installation folder.",
        "root_folder": "The app cannot be installed directly into a drive root.",
        "occupied_folder": (
            "The selected folder already contains files from another program or user. "
            "Choose an empty folder or the previous LinguaFlow AI installation folder."
        ),
    },
    "ru": {
        "language_name": "Русский",
        "title": "Установка LinguaFlow AI",
        "welcome_title": "Добро пожаловать в LinguaFlow AI",
        "release": "Релиз",
        "language": "Язык установки",
        "welcome": "LinguaFlow AI - компактный Windows-переводчик для выделенного текста.",
        "highlight": "Выделите текст в любом приложении, нажмите Ctrl+C+C и получите быстрый popup-перевод.",
        "details": (
            "Приложение также поддерживает обычный ручной перевод, локальную историю переводов "
            "и выбор OpenAI, Google Gemini или Anthropic Claude. "
            "Папка установки по умолчанию: Program Files."
        ),
        "api_note": (
            "После установки нужно ввести личный API-ключ в Настройки -> API. "
            "Инструкция находится в Настройки -> Основное -> Инструкция."
        ),
        "destination_title": "Выберите параметры установки",
        "install_folder": "Папка установки",
        "browse": "Обзор...",
        "options": "Параметры",
        "desktop_shortcut": "Создать ярлык на рабочем столе",
        "start_menu_shortcut": "Добавить ярлык в меню Пуск",
        "launch_after_install": "Запустить LinguaFlow AI после установки",
        "ready": "Готово к установке",
        "stopping": "Закрываю запущенную программу...",
        "extracting": "Распаковываю файлы...",
        "copying": "Копирую файлы приложения...",
        "shortcuts": "Создаю ярлыки...",
        "registering": "Регистрирую удаление в Windows...",
        "launching": "Запускаю LinguaFlow AI...",
        "installing": "Устанавливаю LinguaFlow AI...",
        "failed": "Установка не завершена",
        "completed": "Установка завершена",
        "success": (
            "Установка LinguaFlow AI завершена.\n\n"
            "Для корректной работы необходимо ввести свой API-ключ: Настройки -> API.\n\n"
            "Ответы по работе с программой можно найти в Настройки -> Основное -> Инструкция."
        ),
        "startup_error": "Не удалось запустить установщик LinguaFlow AI.",
        "install_error": "Не удалось установить LinguaFlow AI.",
        "choose_folder": "Выберите папку установки",
        "continue": "Продолжить",
        "back": "Назад",
        "install": "Установить",
        "cancel": "Отмена",
        "empty_folder": "Выберите папку установки.",
        "root_folder": "Нельзя устанавливать программу прямо в корень диска.",
        "occupied_folder": (
            "Выбранная папка уже содержит файлы другой программы или пользователя. "
            "Выберите пустую папку или прежнюю папку установки LinguaFlow AI."
        ),
    },
}


@dataclass(frozen=True)
class InstallOptions:
    install_root: Path
    desktop_shortcut: bool
    start_menu_shortcut: bool
    launch_after_install: bool


class InstallerWizard:
    def __init__(self) -> None:
        configure_process_dpi_awareness()
        self.root = Tk()
        self.root.geometry("760x500")
        self.root.minsize(760, 500)
        self.root.resizable(False, False)
        self._apply_window_icon()

        default_dir = Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / APP_NAME
        self.language_code = StringVar(value="en")
        self.install_dir = StringVar(value=str(default_dir))
        self.desktop_shortcut = BooleanVar(value=True)
        self.start_menu_shortcut = BooleanVar(value=True)
        self.launch_after_install = BooleanVar(value=False)
        self.status = StringVar(value=self.t("ready"))
        self.progress_value = DoubleVar(value=0)
        self.logo_image = self._load_logo()
        self.install_button: ttk.Button | None = None
        self.progress: ttk.Progressbar | None = None

        self.container = ttk.Frame(self.root, padding=24)
        self.container.pack(fill="both", expand=True)
        self._show_welcome_page()

    def run(self) -> int:
        self.root.mainloop()
        return 0

    def t(self, key: str) -> str:
        return INSTALLER_COPY[self.language_code.get()].get(key, INSTALLER_COPY["en"][key])

    def _clear_container(self) -> None:
        for child in self.container.winfo_children():
            child.destroy()

    def _show_welcome_page(self) -> None:
        self.root.title(WINDOW_TITLE)
        self.status.set(self.t("ready"))
        self._clear_container()

        content = ttk.Frame(self.container)
        content.pack(fill="both", expand=True)
        self._build_header(content, self.t("welcome_title"))

        language_row = ttk.Frame(content)
        language_row.pack(fill="x", pady=(16, 22))
        ttk.Label(language_row, text=self.t("language")).pack(side="left")
        language_values = [copy["language_name"] for copy in INSTALLER_COPY.values()]
        language_input = ttk.Combobox(language_row, state="readonly", width=18, values=language_values)
        current_index = list(INSTALLER_COPY).index(self.language_code.get())
        language_input.current(current_index)
        language_input.pack(side="left", padx=(12, 0))
        language_input.bind("<<ComboboxSelected>>", lambda event: self._set_language(event.widget.current()))

        ttk.Label(content, text=self.t("welcome"), wraplength=670, justify="left").pack(anchor="w", pady=(0, 10))
        ttk.Label(
            content,
            text=self.t("highlight"),
            wraplength=670,
            justify="left",
            font=("Segoe UI", 11, "bold"),
        ).pack(anchor="w", pady=(0, 10))
        ttk.Label(content, text=self.t("details"), wraplength=670, justify="left").pack(anchor="w")

        self._build_buttons([(self.t("cancel"), self.root.destroy), (self.t("continue"), self._show_options_page)])

    def _show_options_page(self) -> None:
        self.root.title(WINDOW_TITLE)
        self.status.set(self.t("ready"))
        self._clear_container()

        content = ttk.Frame(self.container)
        content.pack(fill="both", expand=True)
        self._build_header(content, self.t("destination_title"))

        ttk.Label(content, text=self.t("install_folder")).pack(anchor="w", pady=(18, 0))
        path_row = ttk.Frame(content)
        path_row.pack(fill="x", pady=(4, 12))
        ttk.Entry(path_row, textvariable=self.install_dir).pack(side="left", fill="x", expand=True)
        ttk.Button(path_row, text=self.t("browse"), command=self._choose_folder).pack(side="left", padx=(8, 0))

        options_box = ttk.LabelFrame(content, text=self.t("options"))
        options_box.pack(fill="x", pady=(0, 14))
        ttk.Checkbutton(options_box, text=self.t("desktop_shortcut"), variable=self.desktop_shortcut).pack(
            anchor="w", padx=12, pady=(9, 3)
        )
        ttk.Checkbutton(options_box, text=self.t("start_menu_shortcut"), variable=self.start_menu_shortcut).pack(
            anchor="w", padx=12, pady=3
        )
        ttk.Checkbutton(options_box, text=self.t("launch_after_install"), variable=self.launch_after_install).pack(
            anchor="w", padx=12, pady=(3, 9)
        )

        ttk.Label(content, text=self.t("api_note"), wraplength=670, justify="left").pack(anchor="w", pady=(0, 12))
        self.progress = ttk.Progressbar(content, mode="determinate", maximum=100, variable=self.progress_value)
        self.progress.pack(fill="x", pady=(0, 8))
        ttk.Label(content, textvariable=self.status).pack(anchor="w")

        self._build_buttons(
            [
                (self.t("cancel"), self.root.destroy),
                (self.t("install"), self._start_install),
                (self.t("back"), self._show_welcome_page),
            ]
        )

    def _build_header(self, parent: ttk.Frame, title: str) -> None:
        header = ttk.Frame(parent)
        header.pack(fill="x")
        if self.logo_image is not None:
            ttk.Label(header, image=self.logo_image).pack(side="left", padx=(0, 14))
        title_box = ttk.Frame(header)
        title_box.pack(side="left", fill="x", expand=True)
        ttk.Label(title_box, text=title, font=("Segoe UI", 20, "bold")).pack(anchor="w")
        ttk.Label(
            title_box,
            text=f"{self.t('release')} v{APP_VERSION} · Popup Translator - © Roman Ostroumov / Oster",
            foreground="#246b92",
        ).pack(
            anchor="w",
            pady=(2, 0),
        )

    def _build_buttons(self, buttons: list[tuple[str, object]]) -> None:
        button_row = ttk.Frame(self.container)
        button_row.pack(fill="x", side="bottom", pady=(18, 0))
        for text, command in buttons:
            button = ttk.Button(button_row, text=text, command=command)
            button.pack(side="right", padx=(8, 0))
            if text == self.t("install"):
                self.install_button = button

    def _set_language(self, selected_index: int) -> None:
        codes = list(INSTALLER_COPY)
        if 0 <= selected_index < len(codes):
            self.language_code.set(codes[selected_index])
        self._show_welcome_page()

    def _apply_window_icon(self) -> None:
        icon_path = resource_path("app_icon.ico")
        if icon_path.exists():
            try:
                self.root.iconbitmap(str(icon_path))
            except Exception:
                pass

    def _load_logo(self) -> PhotoImage | None:
        image_path = resource_path("installer_logo.png")
        if not image_path.exists():
            return None
        try:
            image = PhotoImage(file=str(image_path))
        except Exception:
            return None
        scale = max(image.width() // 64, image.height() // 64, 1)
        return image.subsample(scale, scale)

    def _choose_folder(self) -> None:
        selected = filedialog.askdirectory(
            title=self.t("choose_folder"),
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
            validate_install_root(options.install_root, self.language_code.get())
        except Exception as exc:  # noqa: BLE001 - user-facing validation.
            messagebox.showerror(self.t("title"), str(exc))
            return

        if self.install_button is not None:
            self.install_button.configure(state="disabled")
        if self.progress is not None:
            self.progress_value.set(0)
        self.status.set(self.t("installing"))

        thread = threading.Thread(target=self._install_in_background, args=(options,), daemon=True)
        thread.start()

    def _install_in_background(self, options: InstallOptions) -> None:
        try:
            install(options, self._report_progress)
        except Exception as exc:  # noqa: BLE001 - user-facing installer.
            self.root.after(0, lambda: self._finish_with_error(exc))
            return
        self.root.after(0, self._finish_success)

    def _finish_with_error(self, exc: Exception) -> None:
        self.progress_value.set(0)
        if self.install_button is not None:
            self.install_button.configure(state="normal")
        self.status.set(self.t("failed"))
        messagebox.showerror(self.t("title"), f"{self.t('install_error')}\n\n{exc}")

    def _finish_success(self) -> None:
        self.progress_value.set(100)
        self.status.set(self.t("completed"))
        messagebox.showinfo(self.t("title"), self.t("success"))
        self.root.destroy()

    def _report_progress(self, value: int, status_key: str) -> None:
        self.root.after(0, lambda: self._apply_progress(value, status_key))

    def _apply_progress(self, value: int, status_key: str) -> None:
        self.progress_value.set(value)
        self.status.set(self.t(status_key))


def main() -> int:
    try:
        configure_process_dpi_awareness()
        return InstallerWizard().run()
    except Exception as exc:  # noqa: BLE001 - last-resort UI fallback.
        show_message("LinguaFlow AI Setup", f"Could not start LinguaFlow AI Setup.\n\n{exc}", icon_error=True)
        return 1


def install(options: InstallOptions, progress: object | None = None) -> None:
    payload = resource_path(PAYLOAD_ZIP)
    if not payload.exists():
        raise FileNotFoundError(f"Installer payload is missing: {payload}")

    install_root = options.install_root.resolve()
    temp_root = Path(tempfile.mkdtemp(prefix="LinguaFlowAIInstall_"))

    try:
        _report(progress, 8, "stopping")
        stop_running_app()

        _report(progress, 22, "extracting")
        with zipfile.ZipFile(payload) as archive:
            archive.extractall(temp_root)

        source_root = temp_root / APP_NAME
        source_exe = source_root / APP_EXE
        if not source_exe.exists():
            raise FileNotFoundError("Installer payload does not contain LinguaFlow AI.exe")

        _report(progress, 46, "copying")
        prepare_install_root(install_root)
        shutil.copytree(source_root, install_root)
        (install_root / MARKER_FILE).write_text(APP_NAME, encoding="utf-8")

        target_exe = install_root / APP_EXE
        uninstall_exe = install_root / UNINSTALL_EXE
        installed_icon = install_root / "_internal" / "assets" / "app_icon.ico"
        shortcut_icon = installed_icon if installed_icon.exists() else target_exe
        if not uninstall_exe.exists():
            raise FileNotFoundError("Installer payload does not contain LinguaFlow AI Uninstall.exe")
        _report(progress, 72, "registering")
        register_uninstall_entry(install_root, target_exe, uninstall_exe, shortcut_icon)
        _report(progress, 86, "shortcuts")
        write_shortcuts(target_exe, shortcut_icon, options)

        if options.launch_after_install:
            _report(progress, 96, "launching")
            subprocess.Popen([str(target_exe)], cwd=str(install_root))
        _report(progress, 100, "completed")
    finally:
        shutil.rmtree(temp_root, ignore_errors=True)


def _report(progress: object | None, value: int, status_key: str) -> None:
    if callable(progress):
        progress(value, status_key)


def validate_install_root(install_root: Path, language_code: str = "en") -> None:
    copy = INSTALLER_COPY.get(language_code, INSTALLER_COPY["en"])
    if not str(install_root).strip():
        raise ValueError(copy["empty_folder"])

    resolved = install_root.resolve()
    if resolved.anchor and str(resolved) == resolved.anchor:
        raise ValueError(copy["root_folder"])

    if resolved.exists() and any(resolved.iterdir()) and not (resolved / MARKER_FILE).exists():
        raise ValueError(copy["occupied_folder"])


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
        startupinfo=hidden_startupinfo(),
        creationflags=hidden_creationflags(),
        check=False,
    )


def write_shortcuts(target_exe: Path, icon_path: Path, options: InstallOptions) -> None:
    if options.desktop_shortcut:
        desktop = Path(os.environ.get("PUBLIC", str(Path.home()))) / "Desktop"
        write_shortcut(desktop / SHORTCUT_NAME, target_exe, icon_path)

    if options.start_menu_shortcut:
        start_menu = Path(os.environ.get("ProgramData", os.environ["APPDATA"])) / "Microsoft" / "Windows" / "Start Menu" / "Programs"
        write_shortcut(start_menu / SHORTCUT_NAME, target_exe, icon_path)


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


def write_shortcut(path: Path, target: Path, icon: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    stale_url_shortcut = path.with_name(URL_SHORTCUT_NAME)
    if stale_url_shortcut.exists():
        stale_url_shortcut.unlink()
    try:
        write_lnk_shortcut(path, target, icon)
    except Exception:
        write_url_shortcut(path.with_suffix(".url"), target, icon)


def write_lnk_shortcut(path: Path, target: Path, icon: Path) -> None:
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
        [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-Command",
            script,
            str(path),
            str(target.resolve()),
            str(icon.resolve()),
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        startupinfo=hidden_startupinfo(),
        creationflags=hidden_creationflags(),
        check=True,
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


def register_uninstall_entry(install_root: Path, target_exe: Path, uninstall_exe: Path, display_icon: Path) -> None:
    uninstall_command = f'"{uninstall_exe}"'
    quiet_uninstall_command = f'"{uninstall_exe}" --quiet'
    estimated_size_kb = sum(file.stat().st_size for file in install_root.rglob("*") if file.is_file()) // 1024

    try:
        root = winreg.HKEY_LOCAL_MACHINE
        key = winreg.CreateKey(root, UNINSTALL_KEY)
    except PermissionError:
        root = winreg.HKEY_CURRENT_USER
        key = winreg.CreateKey(root, UNINSTALL_KEY)

    with key:
        winreg.SetValueEx(key, "DisplayName", 0, winreg.REG_SZ, APP_NAME)
        winreg.SetValueEx(key, "DisplayVersion", 0, winreg.REG_SZ, APP_VERSION)
        winreg.SetValueEx(key, "Publisher", 0, winreg.REG_SZ, APP_PUBLISHER)
        winreg.SetValueEx(key, "InstallLocation", 0, winreg.REG_SZ, str(install_root))
        winreg.SetValueEx(key, "DisplayIcon", 0, winreg.REG_SZ, str(display_icon))
        winreg.SetValueEx(key, "UninstallString", 0, winreg.REG_SZ, uninstall_command)
        winreg.SetValueEx(key, "QuietUninstallString", 0, winreg.REG_SZ, quiet_uninstall_command)
        winreg.SetValueEx(key, "NoModify", 0, winreg.REG_DWORD, 1)
        winreg.SetValueEx(key, "NoRepair", 0, winreg.REG_DWORD, 1)
        winreg.SetValueEx(key, "EstimatedSize", 0, winreg.REG_DWORD, int(estimated_size_kb))


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


if __name__ == "__main__":
    raise SystemExit(main())
