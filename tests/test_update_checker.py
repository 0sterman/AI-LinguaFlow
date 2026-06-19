from translator_app.update_checker import (
    _find_installer_asset,
    compare_versions,
    create_windows_update_helper,
    normalize_version,
    safe_filename,
)


def test_normalize_version_accepts_github_tags() -> None:
    assert normalize_version("v1.0.4") == "1.0.4"
    assert normalize_version("1.2.3-beta") == "1.2.3"


def test_compare_versions() -> None:
    assert compare_versions("1.0.4", "1.0.3") > 0
    assert compare_versions("1.0.3", "1.0.4") < 0
    assert compare_versions("1.0.4", "v1.0.4") == 0


def test_safe_filename_removes_unsafe_characters() -> None:
    assert safe_filename("LinguaFlow<>Setup?.exe") == "LinguaFlow.Setup..exe"


def test_find_installer_asset_uses_dmg_on_macos() -> None:
    payload = {
        "assets": [
            {"name": "LinguaFlow-AI-Setup-v1.0.9.exe", "browser_download_url": "https://example.com/app.exe"},
            {"name": "LinguaFlow AI-1.0.9-macOS-x86_64.dmg", "browser_download_url": "https://example.com/app.dmg"},
        ]
    }
    assert _find_installer_asset(payload, platform="darwin")["name"].endswith(".dmg")


def test_create_windows_update_helper_runs_uninstall_before_installer(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("translator_app.update_checker.tempfile.gettempdir", lambda: str(tmp_path))
    helper = create_windows_update_helper(
        tmp_path / "LinguaFlow-AI-Setup-v1.0.15.exe",
        tmp_path / "LinguaFlow AI Uninstall.exe",
        tmp_path / "LinguaFlow AI",
    )

    content = helper.read_text(encoding="utf-8")
    assert "--preserve-autostart" in content
    assert "--install-root" in content
    assert "Start-Process -FilePath $installer" in content
