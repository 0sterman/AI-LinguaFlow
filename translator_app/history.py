from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from translator_app.config import CONFIG_DIR


HISTORY_PATH = CONFIG_DIR / "history.sqlite3"


@dataclass(frozen=True)
class HistoryRecord:
    id: int
    created_at: str
    source_text: str
    translated_text: str
    source_language: str
    target_language: str
    provider: str
    model: str

    @property
    def local_date_label(self) -> str:
        try:
            parsed = datetime.fromisoformat(self.created_at)
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            local_time = parsed.astimezone()
            return local_time.strftime("%d.%m.%Y %H:%M")
        except ValueError:
            return self.created_at[:16]


class HistoryStore:
    def __init__(self, path: Path = HISTORY_PATH, max_records: int = 500) -> None:
        self.path = path
        self.max_records = max_records
        self._ensure_schema()

    def add(
        self,
        source_text: str,
        translated_text: str,
        target_language: str,
        provider: str,
        model: str,
        source_language: str = "auto",
    ) -> None:
        if not source_text.strip() or not translated_text.strip():
            return
        created_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO translations (
                    created_at,
                    source_text,
                    translated_text,
                    source_language,
                    target_language,
                    provider,
                    model
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (created_at, source_text, translated_text, source_language, target_language, provider, model),
            )
            connection.execute(
                """
                DELETE FROM translations
                WHERE id NOT IN (
                    SELECT id FROM translations
                    ORDER BY id DESC
                    LIMIT ?
                )
                """,
                (self.max_records,),
            )

    def recent(self, limit: int = 100) -> list[HistoryRecord]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT id, created_at, source_text, translated_text, source_language, target_language, provider, model
                FROM translations
                ORDER BY id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [HistoryRecord(*row) for row in rows]

    def search(
        self,
        query: str = "",
        date_from: str | None = None,
        date_to: str | None = None,
        limit: int = 100,
    ) -> list[HistoryRecord]:
        clauses: list[str] = []
        params: list[str | int] = []

        cleaned_query = query.strip()
        if cleaned_query:
            clauses.append("(source_text LIKE ? OR translated_text LIKE ? OR source_language LIKE ? OR target_language LIKE ?)")
            like_query = f"%{cleaned_query}%"
            params.extend([like_query, like_query, like_query, like_query])

        if date_from:
            clauses.append("created_at >= ?")
            params.append(_date_start_iso(date_from))

        if date_to:
            clauses.append("created_at <= ?")
            params.append(_date_end_iso(date_to))

        where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        params.append(limit)
        with self._connect() as connection:
            rows = connection.execute(
                f"""
                SELECT id, created_at, source_text, translated_text, source_language, target_language, provider, model
                FROM translations
                {where_sql}
                ORDER BY id DESC
                LIMIT ?
                """,
                params,
            ).fetchall()
        return [HistoryRecord(*row) for row in rows]

    def clear(self) -> None:
        with self._connect() as connection:
            connection.execute("DELETE FROM translations")

    def _connect(self) -> sqlite3.Connection:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        return sqlite3.connect(self.path)

    def _ensure_schema(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS translations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at TEXT NOT NULL,
                    source_text TEXT NOT NULL,
                    translated_text TEXT NOT NULL,
                    source_language TEXT NOT NULL DEFAULT 'auto',
                    target_language TEXT NOT NULL,
                    provider TEXT NOT NULL,
                    model TEXT NOT NULL
                )
                """
            )
            columns = {row[1] for row in connection.execute("PRAGMA table_info(translations)").fetchall()}
            if "source_language" not in columns:
                connection.execute("ALTER TABLE translations ADD COLUMN source_language TEXT NOT NULL DEFAULT 'auto'")


def _date_start_iso(date_text: str) -> str:
    parsed = datetime.strptime(date_text, "%Y-%m-%d")
    local_tz = datetime.now().astimezone().tzinfo
    local_start = parsed.replace(tzinfo=local_tz)
    return local_start.astimezone(timezone.utc).isoformat(timespec="seconds")


def _date_end_iso(date_text: str) -> str:
    parsed = datetime.strptime(date_text, "%Y-%m-%d").replace(hour=23, minute=59, second=59)
    local_tz = datetime.now().astimezone().tzinfo
    local_end = parsed.replace(tzinfo=local_tz)
    return local_end.astimezone(timezone.utc).isoformat(timespec="seconds")
