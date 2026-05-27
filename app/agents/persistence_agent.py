from app.graph.state import EmailResearchState
from app.storage.sqlite_store import save_summary


def persistence_agent(state: EmailResearchState) -> EmailResearchState:
    # This agent saves user-facing summaries into SQLite.
    saved_ids: list[str] = []
    errors: list[str] = []

    for summary in state.get("summaries", []):
        try:
            saved_ids.append(save_summary(summary))
        except Exception as exc:
            errors.append(f"persistence_agent failed for {summary.email_id}: {exc}")

    return {"saved_summary_ids": saved_ids, "errors": errors}
