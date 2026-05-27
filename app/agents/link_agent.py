from __future__ import annotations

import asyncio

from app.graph.state import EmailResearchState
from app.models import ExtractedDocument


async def _crawl_url(url: str) -> tuple[str, str]:
    from crawl4ai import AsyncWebCrawler

    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun(url=url)
        markdown = getattr(result, "markdown", None) or ""
        title = getattr(result, "title", "") or url
        return title, markdown


def _crawl_url_sync(url: str) -> tuple[str, str]:
    return asyncio.run(_crawl_url(url))


def link_agent(state: EmailResearchState) -> EmailResearchState:
    documents: list[ExtractedDocument] = []
    errors: list[str] = []

    for email in state.get("emails", []):
        for url in email.links:
            try:
                title, text = _crawl_url_sync(url)
                if text.strip():
                    documents.append(
                        ExtractedDocument(
                            source_type="link",
                            source=url,
                            title=title,
                            text=text,
                            email_id=email.id,
                            metadata={"subject": email.subject, "sender": email.sender, "date": email.date},
                        )
                    )
            except Exception as exc:
                errors.append(f"link_agent failed for {url}: {exc}")

    return {"documents": documents, "errors": errors}
