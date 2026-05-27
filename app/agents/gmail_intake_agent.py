from app.config import get_settings
from app.gmail.client import download_attachments, fetch_emails
from app.graph.state import EmailResearchState


def gmail_intake_agent(state: EmailResearchState) -> EmailResearchState:
    # This is the first real agent in the graph.
    # It reads Gmail and downloads any attachments for later agents.
    settings = get_settings()
    query = state.get("gmail_query") or settings.gmail_query
    max_results = state.get("max_results") or settings.gmail_max_results
    since = state.get("since")
    until = state.get("until")

    try:
        emails = fetch_emails(query=query, max_results=max_results, since=since, until=until)

        emails_with_files = []
        for email in emails:
            email_with_files = download_attachments(email)
            emails_with_files.append(email_with_files)

        emails = emails_with_files
        return {"emails": emails}
    except Exception as exc:
        return {"emails": [], "errors": [f"gmail_intake_agent failed: {exc}"]}
