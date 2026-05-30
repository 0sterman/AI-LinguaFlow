import translator_app.platform_text as platform_text


def test_macos_platform_text_keeps_ctrl_inside_parentheses(monkeypatch) -> None:
    monkeypatch.setattr(platform_text.sys, "platform", "darwin")

    assert platform_text.platform_text("Ctrl+C+C") == "Cmd (Ctrl)+C+C"
    assert platform_text.platform_text("Ctrl+Enter") == "Cmd (Ctrl)+Enter"
    assert "Cmd (Cmd)" not in platform_text.platform_text("Ctrl+C+C")

