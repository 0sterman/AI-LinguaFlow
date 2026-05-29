from __future__ import annotations

import ctypes
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path


APP_NAME = "LinguaFlow AI"
APP_EXE = "LinguaFlow AI.exe"
SHORTCUT_NAME = "LinguaFlow AI Translator.url"
PAYLOAD_ZIP = "LinguaFlowAI_payload.zip"


def main() -> int:
    try:
        install()
    except Exception as exc:  # noqa: BLE001 - installer should show the user any failure.
        show_message(
            "LinguaFlow AI Setup",
            f"Не удалось установить LinguaFlow AI.\n\n{exc}",
            icon_error=True,
        )
        return 1

    show_message(
        "LinguaFlow AI Setup",
        "Установка LinguaFlow AI завершена.\n\n"
        "Для корректной работы необходимо ввести свой API-ключ: Настройки -> API.\n\n"
        "Ответы по работе с программой можно найти в Настройки -> Основное -> Инструкция.",
    )
    return 0


def install() -> None:
    payload = resource_path(PAYLOAD_ZIP)
    if not payload.exists():
        raise FileNotFoundError(f"Не найден установочный пакет: {payload}")

    local_app_data = Path(os.environ["LOCALAPPDATA"])
    install_root = local_app_data / "Programs" / APP_NAME
    temp_root = Path(tempfile.mkdtemp(prefix="LinguaFlowAIInstall_"))

    try:
        stop_running_app()

        with zipfile.ZipFile(payload) as archive:
            archive.extractall(temp_root)

        source_root = temp_root / APP_NAME
        source_exe = source_root / APP_EXE
        if not source_exe.exists():
            raise FileNotFoundError("В пакете нет LinguaFlow AI.exe")

        ensure_safe_install_path(install_root, local_app_data)
        if install_root.exists():
            shutil.rmtree(install_root)

        install_root.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(source_root, install_root)

        target_exe = install_root / APP_EXE
        write_shortcuts(target_exe, target_exe)
    finally:
        shutil.rmtree(temp_root, ignore_errors=True)


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


def ensure_safe_install_path(install_root: Path, local_app_data: Path) -> None:
    resolved_install = install_root.resolve()
    resolved_local = local_app_data.resolve()
    install_text = str(resolved_install).casefold()
    local_text = str(resolved_local).casefold()
    if install_text != local_text and not install_text.startswith(local_text + os.sep):
        raise ValueError(f"Небезопасный путь установки: {resolved_install}")


def write_shortcuts(target_exe: Path, icon_path: Path) -> None:
    desktop = Path(os.path.expanduser("~")) / "Desktop"
    start_menu = Path(os.environ["APPDATA"]) / "Microsoft" / "Windows" / "Start Menu" / "Programs"

    write_url_shortcut(desktop / SHORTCUT_NAME, target_exe, icon_path)
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


def show_message(title: str, text: str, icon_error: bool = False) -> None:
    flags = 0x00000010 if icon_error else 0x00000040
    ctypes.windll.user32.MessageBoxW(None, text, title, flags)


if __name__ == "__main__":
    raise SystemExit(main())
