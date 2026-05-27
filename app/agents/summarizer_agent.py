from __future__ import annotations

import json
from collections import defaultdict

from langchain_openai import ChatOpenAI

from app.config import get_settings
from app.graph.state import EmailResearchState
from app.models import EmailSummary


def summarizer_agent(state: EmailResearchState) -> EmailResearchState:
    # This agent groups extracted documents by email and asks the LLM to
    # summarize each email's links/attachments.
    settings = get_settings()
    documents_by_email = defaultdict(list)
    for document in state.get("documents", []):
        documents_by_email[document.email_id].append(document)

    summaries: list[EmailSummary] = []
    llm = ChatOpenAI(model=settings.openai_model, temperature=0)

    for email in state.get("emails", []):
        docs = documents_by_email.get(email.id, [])
        if not docs:
            continue

        # Build the prompt content one document at a time. The 12000 character
        # slice keeps very large files from creating an oversized prompt.
        payload_parts: list[str] = []
        for doc in docs:
            payload_part = f"SOURCE: {doc.source}\nTITLE: {doc.title}\nTEXT:\n{doc.text[:12000]}"
            payload_parts.append(payload_part)
        payload = "\n\n".join(payload_parts)

        prompt = f"""
You summarize links and documents from a user's personal email.
Return strict JSON with these keys:
- short_summary: one concise paragraph
- detailed_summary: two to five paragraphs
- key_points: array of important bullets

Email subject: {email.subject}
From: {email.sender}
Date: {email.date}

Extracted content:
{payload}
"""
        response = llm.invoke(prompt)
        data = _safe_json(response.content)

        sources: list[str] = []
        for doc in docs:
            sources.append(doc.source)

        summaries.append(
            EmailSummary(
                email_id=email.id,
                subject=email.subject,
                sender=email.sender,
                date=email.date,
                received_at=email.received_at,
                short_summary=data.get("short_summary", ""),
                detailed_summary=data.get("detailed_summary", ""),
                key_points=data.get("key_points", []),
                sources=sources,
            )
        )

    return {"summaries": summaries}


def _safe_json(text: str) -> dict:
    # The prompt asks for JSON, but LLMs can sometimes return plain text.
    # This fallback keeps the app useful instead of crashing.
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {
            "short_summary": text[:800],
            "detailed_summary": text,
            "key_points": [],
        }
