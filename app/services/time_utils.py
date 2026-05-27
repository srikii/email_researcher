from __future__ import annotations

from datetime import datetime, timezone
from email.utils import parsedate_to_datetime


def utc_now_iso() -> str:
    # Store times in UTC so comparisons work no matter where the user is.
    return datetime.now(timezone.utc).isoformat()


def parse_user_datetime(value: str | None) -> datetime | None:
    # The browser sends values like 2026-05-27T09:00.
    # If no timezone is included, treat it as the user's local timezone.
    if not value:
        return None

    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        local_tz = datetime.now().astimezone().tzinfo
        dt = dt.replace(tzinfo=local_tz)
    return dt.astimezone(timezone.utc)


def parse_email_date(value: str) -> datetime | None:
    # Gmail's Date header is an email-style string, such as:
    # Wed, 27 May 2026 09:15:00 -0400
    try:
        return parsedate_to_datetime(value).astimezone(timezone.utc)
    except Exception:
        return None


def gmail_after_date(dt: datetime | None) -> str | None:
    # Gmail search wants dates in YYYY/MM/DD format.
    if not dt:
        return None
    return dt.astimezone(timezone.utc).strftime("%Y/%m/%d")
