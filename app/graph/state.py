from __future__ import annotations

import operator
from typing import Annotated, Literal, TypedDict

from app.models import EmailItem, EmailSummary, ExtractedDocument


class EmailResearchState(TypedDict, total=False):
    gmail_query: str
    max_results: int
    emails: list[EmailItem]
    route: Literal["links", "attachments", "both", "empty"]
    documents: Annotated[list[ExtractedDocument], operator.add]
    summaries: list[EmailSummary]
    stored_vector_ids: list[str]
    saved_summary_ids: list[str]
    errors: Annotated[list[str], operator.add]
