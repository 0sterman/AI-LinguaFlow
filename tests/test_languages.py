from translator_app.languages import default_target_language, detect_language_code, is_probably_chinese, is_probably_russian


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


def test_detects_supported_language_hints() -> None:
    assert is_probably_chinese("你好，今天怎么样？") is True
    assert detect_language_code("Das ist nicht gut") == "de"
    assert detect_language_code("Hola, ¿cómo estás?") == "es"
