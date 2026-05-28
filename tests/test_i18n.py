from translator_app.i18n import TRANSLATIONS, t


def test_all_ui_languages_cover_russian_keys() -> None:
    required_keys = set(TRANSLATIONS["ru"])
    for language_code, translations in TRANSLATIONS.items():
        assert required_keys <= set(translations), language_code


def test_unknown_ui_language_falls_back_to_russian() -> None:
    assert t("unknown", "translate") == TRANSLATIONS["ru"]["translate"]
