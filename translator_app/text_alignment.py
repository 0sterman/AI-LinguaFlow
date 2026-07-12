"""Best-effort position mapping between an original text and its translation.

Translations do not retain character offsets.  We therefore preserve paragraph
boundaries and map positions proportionally inside the matching paragraph.  It
is deterministic, works in either direction, and does not send any additional
user text to a provider.
"""

from __future__ import annotations


def map_position(source_text: str, target_text: str, position: int) -> int:
    """Map a cursor position from *source_text* into *target_text*."""
    if not target_text:
        return 0
    if not source_text:
        return 0

    source_spans = _paragraph_spans(source_text)
    target_spans = _paragraph_spans(target_text)
    source_index, source_start, source_end = _span_for_position(source_spans, position)
    target_index = _matching_paragraph_index(source_index, len(source_spans), len(target_spans))
    target_start, target_end = target_spans[target_index]

    source_width = max(1, source_end - source_start)
    target_width = target_end - target_start
    relative_position = min(max(position, source_start), source_end) - source_start
    mapped = target_start + round(relative_position / source_width * target_width)
    return min(max(mapped, target_start), target_end)


def map_selection(source_text: str, target_text: str, start: int, end: int) -> tuple[int, int]:
    """Map a selected source range into the corresponding target range."""
    source_length = len(source_text)
    start = min(max(start, 0), source_length)
    end = min(max(end, 0), source_length)
    if end < start:
        start, end = end, start

    mapped_start = map_position(source_text, target_text, start)
    mapped_end = _map_selection_end(source_text, target_text, end)
    if end > start and mapped_end == mapped_start and mapped_start < len(target_text):
        mapped_end += 1
    return min(mapped_start, mapped_end), max(mapped_start, mapped_end)


def _map_selection_end(source_text: str, target_text: str, end: int) -> int:
    """Map an exclusive selection end without spilling into the next paragraph."""
    source_spans = _paragraph_spans(source_text)
    target_spans = _paragraph_spans(target_text)
    for source_index, (_source_start, source_end) in enumerate(source_spans):
        if end == source_end:
            target_index = _matching_paragraph_index(
                source_index, len(source_spans), len(target_spans)
            )
            return target_spans[target_index][1]
    return map_position(source_text, target_text, end)


def _paragraph_spans(text: str) -> list[tuple[int, int]]:
    spans: list[tuple[int, int]] = []
    start = 0
    for index, character in enumerate(text):
        if character == "\n":
            spans.append((start, index + 1))
            start = index + 1
    if start < len(text) or not spans:
        spans.append((start, len(text)))
    meaningful_spans = [
        (span_start, span_end)
        for span_start, span_end in spans
        if any(character.isalnum() for character in text[span_start:span_end])
    ]
    return meaningful_spans or spans


def _span_for_position(spans: list[tuple[int, int]], position: int) -> tuple[int, int, int]:
    clamped = min(max(position, 0), spans[-1][1])
    for index, (start, end) in enumerate(spans):
        if start <= clamped < end or index == len(spans) - 1:
            return index, start, end
    return len(spans) - 1, *spans[-1]


def _matching_paragraph_index(source_index: int, source_count: int, target_count: int) -> int:
    if source_count <= 1 or target_count <= 1:
        return 0
    return round(source_index * (target_count - 1) / (source_count - 1))
