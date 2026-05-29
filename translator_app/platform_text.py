from __future__ import annotations

import sys


def is_macos() -> bool:
    return sys.platform == "darwin"


def submit_shortcut() -> str:
    return "Cmd+Enter" if is_macos() else "Ctrl+Enter"


def popup_shortcut() -> str:
    return "Cmd+C+C" if is_macos() else "Ctrl+C+C"


def platform_text(text: str) -> str:
    if not is_macos():
        return text
    replacements = {
        "Ctrl+C+C": "Cmd+C+C",
        "Ctrl+Enter": "Cmd+Enter",
        "Ctrl+C": "Cmd+C",
        "Ctrl": "Cmd",
        "Windows Credential Manager": "macOS Keychain",
        "Windows hotkey listener": "macOS hotkey listener",
        "Windows-переводчик": "macOS-переводчик",
        "Windows translator": "macOS translator",
        "Windows-Übersetzer": "macOS-Übersetzer",
        "traductor para Windows": "traductor para macOS",
        "Windows 翻译器": "macOS 翻译器",
        "Start with Windows": "Start with macOS",
        "Запускать с Windows": "Запускать с macOS",
        "Mit Windows starten": "Mit macOS starten",
        "Iniciar con Windows": "Iniciar con macOS",
        "随 Windows 启动": "随 macOS 启动",
    }
    for source, target in replacements.items():
        text = text.replace(source, target)
    return text
