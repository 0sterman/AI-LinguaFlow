from translator_app.update_checker import compare_versions, normalize_version, safe_filename


def test_normalize_version_accepts_github_tags() -> None:
    assert normalize_version("v1.0.4") == "1.0.4"
    assert normalize_version("1.2.3-beta") == "1.2.3"


def test_compare_versions() -> None:
    assert compare_versions("1.0.4", "1.0.3") > 0
    assert compare_versions("1.0.3", "1.0.4") < 0
    assert compare_versions("1.0.4", "v1.0.4") == 0


def test_safe_filename_removes_unsafe_characters() -> None:
    assert safe_filename("LinguaFlow<>Setup?.exe") == "LinguaFlow.Setup..exe"
