import sys

from translator_app import startup


def test_desktop_shortcut_uses_app_name(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(startup, "_known_desktop_path", lambda: tmp_path / "OneDrive" / "Desktop")

    assert startup.desktop_shortcut_path() == tmp_path / "OneDrive" / "Desktop" / "LinguaPopUp AI Translator.lnk"


def test_desktop_shortcut_falls_back_to_home_desktop(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(startup, "_known_desktop_path", lambda: None)
    monkeypatch.setattr(startup.Path, "home", lambda: tmp_path)

    assert startup.desktop_shortcut_path() == tmp_path / "Desktop" / "LinguaPopUp AI Translator.lnk"


def test_url_shortcut_contains_target_and_icon(tmp_path) -> None:
    shortcut = tmp_path / "LinguaPopUp AI Translator.url"

    startup._write_url_shortcut(shortcut, r"C:\App\LinguaPopUp AI.exe", r"C:\App\LinguaPopUp AI.exe")

    content = shortcut.read_text(encoding="utf-8")
    assert "URL=file:///C:/App/LinguaPopUp AI.exe" in content
    assert "IconFile=C:\\App\\LinguaPopUp AI.exe" in content


def test_current_launch_target_uses_executable_when_frozen(monkeypatch) -> None:
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", r"C:\App\LinguaPopUp AI.exe")

    assert startup.current_launch_target() == r"C:\App\LinguaPopUp AI.exe"


def test_current_icon_target_prefers_installed_ico_when_frozen(monkeypatch, tmp_path) -> None:
    exe = tmp_path / "LinguaPopUp AI.exe"
    icon = tmp_path / "_internal" / "assets" / "app_icon.ico"
    icon.parent.mkdir(parents=True)
    icon.write_bytes(b"ico")
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", str(exe))

    assert startup.current_icon_target() == str(icon)


def test_disabling_missing_desktop_shortcut_does_not_crash(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(startup, "_known_desktop_path", lambda: tmp_path)
    monkeypatch.setattr(startup.sys, "platform", "win32")

    startup.set_desktop_shortcut(False)

    assert not (tmp_path / "LinguaPopUp AI Translator.lnk").exists()


def test_start_with_windows_detects_url_fallback(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("APPDATA", str(tmp_path))
    monkeypatch.setattr(startup.sys, "platform", "win32")
    startup_path = startup.startup_shortcut_path()
    startup_path.parent.mkdir(parents=True)
    startup_path.with_name("LinguaPopUp AI Translator.url").write_text("[InternetShortcut]\n", encoding="utf-8")

    assert startup.is_start_with_windows_enabled()


def test_desktop_shortcut_detects_url_fallback(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(startup, "_known_desktop_path", lambda: tmp_path)
    monkeypatch.setattr(startup.sys, "platform", "win32")
    startup.desktop_shortcut_path().with_name("LinguaPopUp AI Translator.url").write_text(
        "[InternetShortcut]\n",
        encoding="utf-8",
    )

    assert startup.is_desktop_shortcut_enabled()

