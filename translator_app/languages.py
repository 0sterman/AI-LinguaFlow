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
CHINESE_RANGES = (("\u4e00", "\u9fff"),)
GERMAN_MARKERS = set("äöüßÄÖÜ")
SPANISH_MARKERS = set("áéíóúñüÁÉÍÓÚÑÜ¿¡")
COMMON_WORDS = {
    "en": {
        "the",
        "and",
        "you",
        "that",
        "this",
        "with",
        "for",
        "not",
        "are",
        "is",
        "we",
        "to",
        "of",
        "in",
    },
    "de": {
        "der",
        "die",
        "das",
        "und",
        "ist",
        "nicht",
        "mit",
        "ein",
        "eine",
        "ich",
        "du",
        "wir",
        "zu",
        "für",
    },
    "es": {
        "el",
        "la",
        "los",
        "las",
        "que",
        "de",
        "y",
        "en",
        "un",
        "una",
        "es",
        "no",
        "por",
        "para",
        "con",
    },
}
FALLBACK_LANGUAGE_BY_PRIMARY = {
    "ru": "en",
    "en": "ru",
    "de": "en",
    "es": "en",
    "zh": "en",
}


def is_probably_russian(text: str) -> bool:
    letters = [char for char in text if char.isalpha()]
    if not letters:
        return False

    russian_count = sum(1 for char in letters if char in RUSSIAN_LETTERS)
    return russian_count / len(letters) >= 0.35


def is_probably_chinese(text: str) -> bool:
    letters = [char for char in text if char.isalpha()]
    if not letters:
        return False

    chinese_count = sum(1 for char in letters if _is_chinese_char(char))
    return chinese_count / len(letters) >= 0.35


def detect_language_code(text: str) -> str | None:
    if is_probably_russian(text):
        return "ru"
    if is_probably_chinese(text):
        return "zh"

    if any(char in GERMAN_MARKERS for char in text):
        return "de"
    if any(char in SPANISH_MARKERS for char in text):
        return "es"

    words = [word.strip(".,!?;:()[]{}\"'").lower() for word in text.split()]
    words = [word for word in words if word]
    if not words:
        return None

    scores = {
        code: sum(1 for word in words if word in markers)
        for code, markers in COMMON_WORDS.items()
    }
    best_code = max(scores, key=scores.get)
    return best_code if scores[best_code] > 0 else None


def default_target_language(text: str, primary_language_code: str = "ru") -> Language:
    primary = get_language(primary_language_code)
    detected_code = detect_language_code(text)
    if detected_code == primary.code:
        fallback_code = FALLBACK_LANGUAGE_BY_PRIMARY.get(primary.code, "en")
        return get_language(fallback_code)
    return primary


def get_language(code: str) -> Language:
    try:
        return LANGUAGE_BY_CODE[code]
    except KeyError as exc:
        raise ValueError(f"Unsupported language code: {code}") from exc


def _is_chinese_char(char: str) -> bool:
    return any(start <= char <= end for start, end in CHINESE_RANGES)
