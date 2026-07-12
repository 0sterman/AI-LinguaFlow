from translator_app.languages import (
    default_target_language,
    detect_language_code,
    is_probably_chinese,
    is_probably_russian,
    next_manual_translation_route,
    preferred_target_language,
)


def test_russian_text_routes_to_english() -> None:
    assert is_probably_russian("Привет, как дела?") is True
    assert default_target_language("Привет, как дела?").code == "en"


def test_non_russian_text_routes_to_russian() -> None:
    assert is_probably_russian("Hello, how are you?") is False
    assert default_target_language("Hello, how are you?").code == "ru"


def test_primary_language_controls_default_target() -> None:
    assert default_target_language("Привет, как дела?", "de").code == "de"
    assert default_target_language("Hola, ¿cómo estás?", "en").code == "en"


def test_text_in_primary_language_routes_to_fallback() -> None:
    assert default_target_language("Hello, how are you?", "en").code == "ru"
    assert default_target_language("你好，今天怎么样？", "zh").code == "en"


def test_preferred_target_language_overrides_default_routing() -> None:
    assert preferred_target_language("Hello, how are you?", "en", "ru").code == "ru"
    assert preferred_target_language("Привет, как дела?", "en", "ru").code == "ru"


def test_invalid_preferred_target_language_falls_back_to_default_routing() -> None:
    assert preferred_target_language("Hello, how are you?", "en", "xx").code == "ru"
    assert preferred_target_language("Hallo, wie geht es dir?", "ru", None).code == "ru"


def test_detects_supported_language_hints() -> None:
    assert is_probably_chinese("你好，今天怎么样？") is True
    assert detect_language_code("Das ist nicht gut") == "de"
    assert detect_language_code("Hola, ¿cómo estás?") == "es"


def test_manual_direction_toggle_returns_to_automatic_source() -> None:
    assert next_manual_translation_route("auto", "ru", "en") == ("ru", "en")
    assert next_manual_translation_route("ru", "ru", "en") == ("auto", "ru")
