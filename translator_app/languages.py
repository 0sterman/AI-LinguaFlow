from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Language:
    code: str
    label: str
    english_name: str


LANGUAGES: tuple[Language, ...] = (
    Language("ru", "RU", "Russian"),
    Language("en", "EN", "English"),
    Language("de", "DE", "German"),
    Language("es", "ES", "Spanish"),
    Language("zh", "ZH", "Simplified Chinese"),
)

LANGUAGE_BY_CODE = {language.code: language for language in LANGUAGES}

RUSSIAN_LETTERS = set("АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯабвгдеёжзийклмнопрстуфхцчшщъыьэюя")


def is_probably_russian(text: str) -> bool:
    letters = [char for char in text if char.isalpha()]
    if not letters:
        return False

    russian_count = sum(1 for char in letters if char in RUSSIAN_LETTERS)
    return russian_count / len(letters) >= 0.35


def default_target_language(text: str) -> Language:
    return LANGUAGE_BY_CODE["en"] if is_probably_russian(text) else LANGUAGE_BY_CODE["ru"]


def get_language(code: str) -> Language:
    try:
        return LANGUAGE_BY_CODE[code]
    except KeyError as exc:
        raise ValueError(f"Unsupported language code: {code}") from exc
