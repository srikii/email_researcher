from app.config import get_settings
from app.gmail.client import download_attachments, fetch_emails
from app.graph.state import EmailResearchState


def gmail_intake_agent(state: EmailResearchState) -> EmailResearchState:
    settings = get_settings()
    query = state.get("gmail_query") or settings.gmail_query
    max_results = state.get("max_results") or settings.gmail_max_results

    try:
        emails = fetch_emails(query=query, max_results=max_results)
        emails = [download_attachments(email) for email in emails]
        return {"emails": emails}
    except Exception as exc:
        return {"emails": [], "errors": [f"gmail_intake_agent failed: {exc}"]}
