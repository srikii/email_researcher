from __future__ import annotations

import json
import sqlite3

from app.config import get_settings
from app.models import EmailSummary


def get_connection():
    settings = get_settings()
    return sqlite3.connect(settings.sqlite_path)


def init_db() -> None:
    with get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS email_summaries (
                email_id TEXT PRIMARY KEY,
                subject TEXT NOT NULL,
                sender TEXT NOT NULL,
                date TEXT NOT NULL,
                short_summary TEXT NOT NULL,
                detailed_summary TEXT NOT NULL,
                key_points_json TEXT NOT NULL,
                sources_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )


def save_summary(summary: EmailSummary) -> str:
    init_db()
    with get_connection() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO email_summaries (
                email_id, subject, sender, date, short_summary, detailed_summary,
                key_points_json, sources_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                summary.email_id,
                summary.subject,
                summary.sender,
                summary.date,
                summary.short_summary,
                summary.detailed_summary,
                json.dumps(summary.key_points),
                json.dumps(summary.sources),
                summary.created_at.isoformat(),
            ),
        )
    return summary.email_id


def list_summaries(limit: int = 50) -> list[dict]:
    init_db()
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT * FROM email_summaries ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [_row_to_dict(row) for row in rows]


def get_summary(email_id: str) -> dict | None:
    init_db()
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT * FROM email_summaries WHERE email_id = ?", (email_id,)).fetchone()
    return _row_to_dict(row) if row else None


def _row_to_dict(row) -> dict:
    item = dict(row)
    item["key_points"] = json.loads(item.pop("key_points_json"))
    item["sources"] = json.loads(item.pop("sources_json"))
    return item
