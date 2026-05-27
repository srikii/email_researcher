from __future__ import annotations

import operator
from typing import Annotated, Literal, TypedDict

from app.models import EmailItem, EmailSummary, ExtractedDocument


class EmailResearchState(TypedDict, total=False):
    # This dictionary is the shared "memory" passed from one LangGraph node
    # to the next. Each agent reads fields it needs and returns fields it changed.
    gmail_query: str
    max_results: int
    since: str
    until: str
    emails: list[EmailItem]
    route: Literal["links", "attachments", "both", "empty"]
    # operator.add tells LangGraph how to merge documents when two branches
    # run at the same time, such as link_agent and attachment_agent.
    documents: Annotated[list[ExtractedDocument], operator.add]
    summaries: list[EmailSummary]
    stored_vector_ids: list[str]
    saved_summary_ids: list[str]
    # Errors are collected instead of immediately crashing the whole graph.
    errors: Annotated[list[str], operator.add]
