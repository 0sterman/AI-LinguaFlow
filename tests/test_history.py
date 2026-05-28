from translator_app.history import HistoryStore


def test_history_store_saves_recent_records(tmp_path) -> None:
    store = HistoryStore(tmp_path / "history.sqlite3", max_records=10)

    store.add("Hello", "Привет", "ru", "openai", "gpt-5-mini")

    records = store.recent()
    assert len(records) == 1
    assert records[0].source_text == "Hello"
    assert records[0].translated_text == "Привет"
    assert records[0].target_language == "ru"


def test_history_store_keeps_latest_records_only(tmp_path) -> None:
    store = HistoryStore(tmp_path / "history.sqlite3", max_records=2)

    store.add("one", "один", "ru", "openai", "gpt-5-mini")
    store.add("two", "два", "ru", "openai", "gpt-5-mini")
    store.add("three", "три", "ru", "openai", "gpt-5-mini")

    records = store.recent()
    assert [record.source_text for record in records] == ["three", "two"]


def test_history_store_clear_removes_records(tmp_path) -> None:
    store = HistoryStore(tmp_path / "history.sqlite3", max_records=10)
    store.add("Hello", "Привет", "ru", "openai", "gpt-5-mini")

    store.clear()

    assert store.recent() == []
