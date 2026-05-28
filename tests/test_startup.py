import sys

from translator_app import startup


def test_desktop_shortcut_uses_app_name(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(startup, "_known_desktop_path", lambda: tmp_path / "OneDrive" / "Desktop")

    assert startup.desktop_shortcut_path() == tmp_path / "OneDrive" / "Desktop" / "AI-LinguaFlow.url"


def test_desktop_shortcut_falls_back_to_home_desktop(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(startup, "_known_desktop_path", lambda: None)
    monkeypatch.setattr(startup.Path, "home", lambda: tmp_path)

    assert startup.desktop_shortcut_path() == tmp_path / "Desktop" / "AI-LinguaFlow.url"


def test_url_shortcut_contains_target_and_icon(tmp_path) -> None:
    shortcut = tmp_path / "AI-LinguaFlow.url"

    startup._write_url_shortcut(shortcut, r"C:\App\WindowsTranslator.exe", r"C:\App\WindowsTranslator.exe")

    content = shortcut.read_text(encoding="utf-8")
    assert "URL=file:///C:/App/WindowsTranslator.exe" in content
    assert "IconFile=C:\\App\\WindowsTranslator.exe" in content


def test_current_launch_target_uses_executable_when_frozen(monkeypatch) -> None:
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", r"C:\App\WindowsTranslator.exe")

    assert startup.current_launch_target() == r"C:\App\WindowsTranslator.exe"
