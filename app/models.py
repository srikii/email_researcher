from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


# Pydantic models describe the shape of data moving through the app.
# They also validate that required fields are present.
class AttachmentInfo(BaseModel):
    # Gmail gives us an attachment_id first. We download it later and fill local_path.
    filename: str
    mime_type: str
    attachment_id: str
    local_path: str | None = None


class EmailItem(BaseModel):
    # This is one Gmail message after we parse the Gmail API response.
    id: str
    thread_id: str
    subject: str
    sender: str
    recipients: list[str] = Field(default_factory=list)
    date: str
    received_at: str
    snippet: str = ""
    body_text: str = ""
    links: list[str] = Field(default_factory=list)
    attachments: list[AttachmentInfo] = Field(default_factory=list)


class ExtractedDocument(BaseModel):
    # This represents text extracted from either a URL or an attachment.
    source_type: Literal["link", "attachment"]
    source: str
    title: str = ""
    text: str
    email_id: str
    metadata: dict = Field(default_factory=dict)


class EmailSummary(BaseModel):
    # This is the final summary users see in the UI.
    email_id: str
    subject: str
    sender: str
    date: str
    received_at: str
    short_summary: str
    detailed_summary: str
    key_points: list[str] = Field(default_factory=list)
    sources: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class SearchRequest(BaseModel):
    # Request body for semantic search.
    query: str
    limit: int = 5


class ProcessRequest(BaseModel):
    # Optional filters for processing Gmail.
    # If since/until are empty, the app uses the saved "new mail" cursor.
    gmail_query: str | None = None
    max_results: int | None = None
    since: str | None = None
    until: str | None = None
