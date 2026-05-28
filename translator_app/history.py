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
    target_language: str
    provider: str
    model: str


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
                    target_language,
                    provider,
                    model
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (created_at, source_text, translated_text, target_language, provider, model),
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
                SELECT id, created_at, source_text, translated_text, target_language, provider, model
                FROM translations
                ORDER BY id DESC
                LIMIT ?
                """,
                (limit,),
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
                    target_language TEXT NOT NULL,
                    provider TEXT NOT NULL,
                    model TEXT NOT NULL
                )
                """
            )
