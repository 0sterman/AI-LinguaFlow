from translator_app.languages import default_target_language, is_probably_russian


def test_russian_text_routes_to_english() -> None:
    assert is_probably_russian("Привет, как дела?") is True
    assert default_target_language("Привет, как дела?").code == "en"


def test_non_russian_text_routes_to_russian() -> None:
    assert is_probably_russian("Hello, how are you?") is False
    assert default_target_language("Hello, how are you?").code == "ru"
