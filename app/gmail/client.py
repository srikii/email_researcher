from __future__ import annotations

import base64
import re
from datetime import datetime, timezone
from email.utils import getaddresses
from pathlib import Path

from bs4 import BeautifulSoup
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from app.config import get_settings
from app.models import AttachmentInfo, EmailItem
from app.services.time_utils import gmail_after_date, parse_user_datetime


SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
URL_RE = re.compile(r"https?://[^\s<>\")]+")


def get_gmail_service():
    # Gmail uses OAuth. The first run opens a browser login flow and writes
    # token.json. Later runs reuse token.json.
    settings = get_settings()
    creds = None
    token_path = Path(settings.google_token_file)

    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(settings.google_credentials_file, SCOPES)
            creds = flow.run_local_server(port=0)
        token_path.write_text(creds.to_json(), encoding="utf-8")

    return build("gmail", "v1", credentials=creds)


def authorize_gmail() -> None:
    # Small helper used by scripts/authorize_gmail.py.
    get_gmail_service()


def fetch_emails(
    query: str,
    max_results: int,
    since: str | None = None,
    until: str | None = None,
) -> list[EmailItem]:
    # Fetch message IDs from Gmail, then fetch and parse each full message.
    service = get_gmail_service()
    since_dt = parse_user_datetime(since)
    until_dt = parse_user_datetime(until)

    # Gmail's search syntax supports dates, but not exact times.
    # We use after:YYYY/MM/DD to reduce results, then filter exact times in Python.
    gmail_query = _build_gmail_query(query, since_dt)
    result = service.users().messages().list(userId="me", q=gmail_query, maxResults=max_results).execute()
    messages = result.get("messages", [])

    emails: list[EmailItem] = []
    for message in messages:
        email = parse_message(service, message["id"])
        if _is_inside_window(email.received_at, since_dt, until_dt):
            emails.append(email)

    return emails


def parse_message(service, message_id: str) -> EmailItem:
    # "format=full" gives us headers, body parts, and attachment metadata.
    message = service.users().messages().get(userId="me", id=message_id, format="full").execute()
    payload = message.get("payload", {})

    headers = {}
    for header in payload.get("headers", []):
        header_name = header["name"].lower()
        headers[header_name] = header["value"]

    parts = list(_walk_parts(payload))

    body_chunks: list[str] = []
    for part in parts:
        decoded_text = _decode_body_part(part)
        if decoded_text:
            body_chunks.append(decoded_text)
    body_text = "\n\n".join(body_chunks)

    links = _extract_all_links(parts, body_text)

    attachments: list[AttachmentInfo] = []
    for part in parts:
        filename = part.get("filename")
        body = part.get("body", {})
        attachment_id = body.get("attachmentId")
        if filename and attachment_id:
            attachments.append(
                AttachmentInfo(
                    filename=filename,
                    mime_type=part.get("mimeType", "application/octet-stream"),
                    attachment_id=attachment_id,
                )
            )

    recipients: list[str] = []
    for name, address in getaddresses([headers.get("to", "")]):
        if address:
            recipients.append(address)

    received_at = _internal_date_to_iso(message.get("internalDate"))
    return EmailItem(
        id=message["id"],
        thread_id=message.get("threadId", ""),
        subject=headers.get("subject", "(no subject)"),
        sender=headers.get("from", ""),
        recipients=recipients,
        date=headers.get("date", ""),
        received_at=received_at,
        snippet=message.get("snippet", ""),
        body_text=body_text,
        links=links,
        attachments=attachments,
    )


def download_attachments(email: EmailItem) -> EmailItem:
    # This writes Gmail attachment bytes to data/attachments/<email_id>/.
    if not email.attachments:
        return email

    settings = get_settings()
    service = get_gmail_service()
    target_dir = Path(settings.attachment_dir) / email.id
    target_dir.mkdir(parents=True, exist_ok=True)

    updated = []
    for attachment in email.attachments:
        response = (
            service.users()
            .messages()
            .attachments()
            .get(userId="me", messageId=email.id, id=attachment.attachment_id)
            .execute()
        )
        data = base64.urlsafe_b64decode(response["data"].encode("utf-8"))
        safe_name = re.sub(r"[^A-Za-z0-9._-]+", "_", attachment.filename)
        path = target_dir / safe_name
        path.write_bytes(data)
        updated.append(attachment.model_copy(update={"local_path": str(path)}))

    return email.model_copy(update={"attachments": updated})


def _walk_parts(part: dict):
    # Gmail messages can be nested. This generator yields the current part,
    # then recursively yields any child parts.
    yield part
    for child in part.get("parts", []) or []:
        yield from _walk_parts(child)


def _decode_body_part(part: dict) -> str:
    # Convert a Gmail text/plain or text/html body part into readable text.
    mime_type = part.get("mimeType", "")
    data = part.get("body", {}).get("data")
    if not data or mime_type not in {"text/plain", "text/html"}:
        return ""

    raw = base64.urlsafe_b64decode(data.encode("utf-8")).decode("utf-8", errors="ignore")
    if mime_type == "text/html":
        return BeautifulSoup(raw, "html.parser").get_text("\n")
    return raw


def _extract_links_from_part(part: dict) -> list[str]:
    # HTML emails often hide URLs inside <a href="..."> tags.
    if part.get("mimeType") != "text/html":
        return []
    data = part.get("body", {}).get("data")
    if not data:
        return []

    raw = base64.urlsafe_b64decode(data.encode("utf-8")).decode("utf-8", errors="ignore")
    soup = BeautifulSoup(raw, "html.parser")
    links: list[str] = []
    for tag in soup.find_all("a"):
        href = tag.get("href", "")
        if href.startswith(("http://", "https://")):
            links.append(href)

    return links


def _extract_all_links(parts: list[dict], body_text: str) -> list[str]:
    # Find links that appear as visible text.
    found_links = set()
    for link in URL_RE.findall(body_text):
        found_links.add(link)

    # Find links that are stored in HTML href attributes.
    for part in parts:
        html_links = _extract_links_from_part(part)
        for link in html_links:
            found_links.add(link)

    return sorted(found_links)


def _internal_date_to_iso(value: str | None) -> str:
    # Gmail internalDate is milliseconds since the Unix epoch.
    if not value:
        return datetime.now(timezone.utc).isoformat()
    return datetime.fromtimestamp(int(value) / 1000, tz=timezone.utc).isoformat()


def _build_gmail_query(query: str, since_dt: datetime | None) -> str:
    # Add a broad Gmail date filter when we have a cursor/range start.
    after = gmail_after_date(since_dt)
    if not after:
        return query
    return f"{query} after:{after}"


def _is_inside_window(received_at: str, since_dt: datetime | None, until_dt: datetime | None) -> bool:
    # This does the exact timestamp filtering after Gmail returns results.
    received_dt = parse_user_datetime(received_at)
    if since_dt and received_dt and received_dt < since_dt:
        return False
    if until_dt and received_dt and received_dt >= until_dt:
        return False
    return True
