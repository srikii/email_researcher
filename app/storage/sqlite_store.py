from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone

from app.config import get_settings
from app.models import EmailSummary
from app.services.time_utils import parse_user_datetime, utc_now_iso


def get_connection():
    # Open a new SQLite connection. The caller usually uses it in a with block
    # so it commits and closes automatically.
    settings = get_settings()
    return sqlite3.connect(settings.sqlite_path)


def init_db() -> None:
    # Create tables if they do not exist yet.
    with get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS email_summaries (
                email_id TEXT PRIMARY KEY,
                subject TEXT NOT NULL,
                sender TEXT NOT NULL,
                date TEXT NOT NULL,
                received_at TEXT NOT NULL DEFAULT '',
                short_summary TEXT NOT NULL,
                detailed_summary TEXT NOT NULL,
                key_points_json TEXT NOT NULL,
                sources_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        _ensure_column(conn, "email_summaries", "received_at", "TEXT NOT NULL DEFAULT ''")
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS app_state (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
            """
        )
        _init_cursor(conn)


def save_summary(summary: EmailSummary) -> str:
    # INSERT OR REPLACE means reprocessing the same email updates its summary.
    init_db()
    with get_connection() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO email_summaries (
                email_id, subject, sender, date, received_at, short_summary, detailed_summary,
                key_points_json, sources_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                summary.email_id,
                summary.subject,
                summary.sender,
                summary.date,
                summary.received_at,
                summary.short_summary,
                summary.detailed_summary,
                json.dumps(summary.key_points),
                json.dumps(summary.sources),
                summary.created_at.isoformat(),
            ),
        )
    return summary.email_id


def list_summaries(limit: int = 50, since: str | None = None, until: str | None = None) -> list[dict]:
    # Build the SQL query step by step so optional date filters are easy to read.
    init_db()
    since_dt = parse_user_datetime(since)
    until_dt = parse_user_datetime(until)
    clauses = []
    params: list = []
    if since_dt:
        clauses.append("received_at >= ?")
        params.append(since_dt.isoformat())
    if until_dt:
        clauses.append("received_at < ?")
        params.append(until_dt.isoformat())
    where = ""
    if clauses:
        where = "WHERE " + " AND ".join(clauses)

    params.append(limit)

    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            f"SELECT * FROM email_summaries {where} ORDER BY received_at DESC LIMIT ?",
            params,
        ).fetchall()
    summaries: list[dict] = []
    for row in rows:
        summaries.append(_row_to_dict(row))
    return summaries


def get_summary(email_id: str) -> dict | None:
    # Fetch one summary by Gmail message ID.
    init_db()
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT * FROM email_summaries WHERE email_id = ?", (email_id,)).fetchone()
    return _row_to_dict(row) if row else None


def _row_to_dict(row) -> dict:
    # SQLite stores lists as JSON strings. Convert them back to Python lists.
    item = dict(row)
    item["key_points"] = json.loads(item.pop("key_points_json"))
    item["sources"] = json.loads(item.pop("sources_json"))
    return item


def get_app_state(key: str) -> str | None:
    # app_state is a tiny key/value table for things like the Gmail cursor.
    init_db()
    with get_connection() as conn:
        row = conn.execute("SELECT value FROM app_state WHERE key = ?", (key,)).fetchone()
    return row[0] if row else None


def set_app_state(key: str, value: str) -> None:
    # Save or update one app_state value.
    init_db()
    with get_connection() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO app_state (key, value) VALUES (?, ?)",
            (key, value),
        )


def get_processing_cursor() -> str:
    # The cursor marks where "new mail" processing should begin.
    init_db()
    cursor = get_app_state("gmail_cursor_started_at")
    if cursor:
        return cursor
    cursor = utc_now_iso()
    set_app_state("gmail_cursor_started_at", cursor)
    return cursor


def advance_processing_cursor(value: str) -> None:
    # Move the cursor forward after a normal processing run.
    set_app_state("gmail_cursor_started_at", value)


def _init_cursor(conn: sqlite3.Connection) -> None:
    # On the first app startup, set the cursor to now.
    # That prevents the app from processing every old Gmail message.
    row = conn.execute("SELECT value FROM app_state WHERE key = ?", ("gmail_cursor_started_at",)).fetchone()
    if row:
        return
    conn.execute(
        "INSERT INTO app_state (key, value) VALUES (?, ?)",
        ("gmail_cursor_started_at", datetime.now(timezone.utc).isoformat()),
    )


def _ensure_column(conn: sqlite3.Connection, table: str, column: str, definition: str) -> None:
    # Simple migration helper for people who already created the DB before
    # received_at existed.
    columns = []
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    for row in rows:
        column_name = row[1]
        columns.append(column_name)

    if column not in columns:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
