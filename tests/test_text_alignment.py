from translator_app.text_alignment import map_position, map_selection


def test_map_selection_keeps_matching_paragraphs() -> None:
    source = "One short paragraph.\nSecond paragraph."
    translation = "Первый абзац.\nВторой абзац здесь длиннее."

    start = source.index("Second")
    end = len(source)

    mapped_start, mapped_end = map_selection(source, translation, start, end)

    assert translation[mapped_start:mapped_end].startswith("Второй")
    assert mapped_end == len(translation)


def test_map_position_maps_viewport_top_bidirectionally() -> None:
    source = "A\nB\nC"
    translation = "один\nдва\nтри"

    assert map_position(source, translation, source.index("B")) == translation.index("два")
    assert map_position(translation, source, translation.index("три")) == source.index("C")


def test_mapping_ignores_a_stray_punctuation_line_in_translation() -> None:
    source = "Portfolio\nDrive systems\nE-Houses"
    translation = ".\nПортфель\nПриводные системы\nЭлектрощитовые"

    start = source.index("E-Houses")
    mapped_start, mapped_end = map_selection(source, translation, start, len(source))

    assert translation[mapped_start:mapped_end].startswith("Электрощитовые")


def test_selection_ending_after_a_paragraph_does_not_include_the_next_one() -> None:
    source = "First paragraph.\nSecond paragraph."
    translation = "Первый абзац.\nВторой абзац."

    source_end = source.index("Second")
    mapped_start, mapped_end = map_selection(source, translation, 0, source_end)

    assert translation[mapped_start:mapped_end] == "Первый абзац.\n"
