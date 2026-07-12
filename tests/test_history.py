import sqlite3

from translator_app.history import HistoryStore


def test_history_store_saves_recent_records(tmp_path) -> None:
    store = HistoryStore(tmp_path / "history.sqlite3", max_records=10)

    store.add("Hello", "Привет", "ru", "openai", "gpt-5-mini", source_language="en")

    records = store.recent()
    assert len(records) == 1
    assert records[0].source_text == "Hello"
    assert records[0].translated_text == "Привет"
    assert records[0].source_language == "en"
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


def test_history_store_search_matches_source_and_translation(tmp_path) -> None:
    store = HistoryStore(tmp_path / "history.sqlite3", max_records=10)
    store.add("Hello world", "Привет мир", "ru", "openai", "gpt-5-mini")
    store.add("Good morning", "Доброе утро", "ru", "openai", "gpt-5-mini")

    assert [record.source_text for record in store.search("утро")] == ["Good morning"]
    assert [record.source_text for record in store.search("world")] == ["Hello world"]


def test_history_store_search_matches_language_route(tmp_path) -> None:
    store = HistoryStore(tmp_path / "history.sqlite3", max_records=10)
    store.add("Hallo", "Привет", "ru", "openai", "gpt-5-mini", source_language="de")

    assert [record.source_text for record in store.search("de")] == ["Hallo"]


def test_history_store_migrates_old_schema(tmp_path) -> None:
    path = tmp_path / "history.sqlite3"
    with sqlite3.connect(path) as connection:
        connection.execute(
            """
            CREATE TABLE translations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                source_text TEXT NOT NULL,
                translated_text TEXT NOT NULL,
                target_language TEXT NOT NULL,
                provider TEXT NOT NULL,
                model TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            INSERT INTO translations (
                created_at, source_text, translated_text, target_language, provider, model
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            ("2026-05-29T00:00:00+00:00", "Hello", "Привет", "ru", "openai", "gpt-5-mini"),
        )

    store = HistoryStore(path, max_records=10)
    records = store.recent()

    assert records[0].source_language == "auto"
    assert records[0].target_language == "ru"


def test_history_store_search_filters_by_date_range(tmp_path) -> None:
    store = HistoryStore(tmp_path / "history.sqlite3", max_records=10)
    store.add("old", "старый", "ru", "openai", "gpt-5-mini")
    store.add("new", "новый", "ru", "openai", "gpt-5-mini")

    with store._connect() as connection:
        connection.execute("UPDATE translations SET created_at = ? WHERE source_text = ?", ("2024-01-01T12:00:00+00:00", "old"))
        connection.execute("UPDATE translations SET created_at = ? WHERE source_text = ?", ("2026-05-28T12:00:00+00:00", "new"))

    records = store.search(date_from="2026-01-01", date_to="2026-12-31")
    assert [record.source_text for record in records] == ["new"]


def test_history_store_returns_most_used_target_for_source(tmp_path) -> None:
    store = HistoryStore(tmp_path / "history.sqlite3", max_records=10)
    store.add("Привет", "Hello", "en", "openai", "gpt-5-mini", source_language="ru")
    store.add("Как дела?", "How are you?", "en", "openai", "gpt-5-mini", source_language="ru")
    store.add("Спасибо", "Danke", "de", "openai", "gpt-5-mini", source_language="ru")
    store.add("Это не должно учитываться", "То же", "ru", "openai", "gpt-5-mini", source_language="ru")

    assert store.most_frequent_target_for_source("ru") == "en"
    assert store.most_frequent_target_for_source("zh") == "en"
