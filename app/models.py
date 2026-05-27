from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class AttachmentInfo(BaseModel):
    filename: str
    mime_type: str
    attachment_id: str
    local_path: str | None = None


class EmailItem(BaseModel):
    id: str
    thread_id: str
    subject: str
    sender: str
    recipients: list[str] = Field(default_factory=list)
    date: str
    snippet: str = ""
    body_text: str = ""
    links: list[str] = Field(default_factory=list)
    attachments: list[AttachmentInfo] = Field(default_factory=list)


class ExtractedDocument(BaseModel):
    source_type: Literal["link", "attachment"]
    source: str
    title: str = ""
    text: str
    email_id: str
    metadata: dict = Field(default_factory=dict)


class EmailSummary(BaseModel):
    email_id: str
    subject: str
    sender: str
    date: str
    short_summary: str
    detailed_summary: str
    key_points: list[str] = Field(default_factory=list)
    sources: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class SearchRequest(BaseModel):
    query: str
    limit: int = 5


class ProcessRequest(BaseModel):
    gmail_query: str | None = None
    max_results: int | None = None
