from installer import installer_app


def test_find_existing_install_root_prefers_registered_linguaflow_root(monkeypatch, tmp_path) -> None:
    registered_root = tmp_path / "registered" / "LinguaPopUp AI"
    target_root = tmp_path / "target" / "LinguaPopUp AI"
    registered_root.mkdir(parents=True)
    target_root.mkdir(parents=True)
    (registered_root / "LinguaPopUp AI.exe").write_bytes(b"exe")

    monkeypatch.setattr(installer_app, "read_registered_install_location", lambda: registered_root)

    assert installer_app.find_existing_install_root(target_root) == registered_root


def test_find_existing_install_root_uses_target_linguaflow_root(monkeypatch, tmp_path) -> None:
    target_root = tmp_path / "LinguaPopUp AI"
    target_root.mkdir()
    (target_root / "LinguaPopUp AI Uninstall.exe").write_bytes(b"exe")

    monkeypatch.setattr(installer_app, "read_registered_install_location", lambda: None)

    assert installer_app.find_existing_install_root(target_root) == target_root

