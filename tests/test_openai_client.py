import pytest

from translator_app.languages import get_language
from translator_app.openai_client import (
    MissingApiKeyError,
    OpenAITranslator,
    ProviderTranslator,
    TranslationError,
    TranslationRequest,
    build_anthropic_payload,
    build_gemini_payload,
    build_translation_payload,
)


def test_payload_requests_only_translation() -> None:
    payload = build_translation_payload(
        TranslationRequest(text="Hello", target_language=get_language("ru"), model="gpt-5-mini")
    )

    assert payload["model"] == "gpt-5-mini"
    assert "Return only the translated text" in payload["instructions"]
    assert "Target language: Russian" in payload["input"]
    assert "Hello" in payload["input"]


def test_empty_text_raises_translation_error() -> None:
    translator = OpenAITranslator(api_key="test")

    with pytest.raises(TranslationError, match="Нет текста"):
        translator.translate("   ", get_language("ru"))


def test_missing_api_key_raises_before_network() -> None:
    translator = OpenAITranslator(api_key=None)

    with pytest.raises(MissingApiKeyError):
        translator.translate("Hello", get_language("ru"))


def test_gemini_payload_requests_plain_translation() -> None:
    payload = build_gemini_payload(
        TranslationRequest(text="Hallo", target_language=get_language("ru"), model="gemini-2.5-flash-lite")
    )

    assert "Return only the translated text" in payload["system_instruction"]["parts"][0]["text"]
    assert "Target language: Russian" in payload["contents"][0]["parts"][0]["text"]
    assert payload["generationConfig"]["responseMimeType"] == "text/plain"


def test_anthropic_payload_requests_plain_translation() -> None:
    payload = build_anthropic_payload(
        TranslationRequest(text="Hola", target_language=get_language("en"), model="claude-3-5-haiku-latest")
    )

    assert payload["model"] == "claude-3-5-haiku-latest"
    assert "Return only the translated text" in payload["system"]
    assert "Target language: English" in payload["messages"][0]["content"]


def test_provider_translator_reports_missing_selected_key() -> None:
    translator = ProviderTranslator(provider="google", api_key=None, model="gemini-2.5-flash-lite")

    with pytest.raises(MissingApiKeyError, match="Google"):
        translator.translate("Hello", get_language("ru"))
