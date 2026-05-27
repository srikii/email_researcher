from __future__ import annotations

import base64
import re
from email.utils import getaddresses
from pathlib import Path

from bs4 import BeautifulSoup
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from app.config import get_settings
from app.models import AttachmentInfo, EmailItem


SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
URL_RE = re.compile(r"https?://[^\s<>\")]+")


def get_gmail_service():
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
    get_gmail_service()


def fetch_emails(query: str, max_results: int) -> list[EmailItem]:
    service = get_gmail_service()
    result = service.users().messages().list(userId="me", q=query, maxResults=max_results).execute()
    messages = result.get("messages", [])
    return [parse_message(service, message["id"]) for message in messages]


def parse_message(service, message_id: str) -> EmailItem:
    message = service.users().messages().get(userId="me", id=message_id, format="full").execute()
    payload = message.get("payload", {})
    headers = {h["name"].lower(): h["value"] for h in payload.get("headers", [])}

    parts = list(_walk_parts(payload))
    body_text = "\n\n".join(filter(None, (_decode_body_part(p) for p in parts)))
    links = sorted(set(URL_RE.findall(body_text) + [link for p in parts for link in _extract_links_from_part(p)]))

    attachments = []
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

    recipients = [addr for _, addr in getaddresses([headers.get("to", "")])]
    return EmailItem(
        id=message["id"],
        thread_id=message.get("threadId", ""),
        subject=headers.get("subject", "(no subject)"),
        sender=headers.get("from", ""),
        recipients=recipients,
        date=headers.get("date", ""),
        snippet=message.get("snippet", ""),
        body_text=body_text,
        links=links,
        attachments=attachments,
    )


def download_attachments(email: EmailItem) -> EmailItem:
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
    yield part
    for child in part.get("parts", []) or []:
        yield from _walk_parts(child)


def _decode_body_part(part: dict) -> str:
    mime_type = part.get("mimeType", "")
    data = part.get("body", {}).get("data")
    if not data or mime_type not in {"text/plain", "text/html"}:
        return ""

    raw = base64.urlsafe_b64decode(data.encode("utf-8")).decode("utf-8", errors="ignore")
    if mime_type == "text/html":
        return BeautifulSoup(raw, "html.parser").get_text("\n")
    return raw


def _extract_links_from_part(part: dict) -> list[str]:
    if part.get("mimeType") != "text/html":
        return []
    data = part.get("body", {}).get("data")
    if not data:
        return []

    raw = base64.urlsafe_b64decode(data.encode("utf-8")).decode("utf-8", errors="ignore")
    soup = BeautifulSoup(raw, "html.parser")
    hrefs = [tag.get("href", "") for tag in soup.find_all("a")]
    return [href for href in hrefs if href.startswith(("http://", "https://"))]
