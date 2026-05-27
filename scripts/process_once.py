from app.config import get_settings
from app.graph.workflow import email_research_graph
from app.services.time_utils import utc_now_iso
from app.storage.sqlite_store import advance_processing_cursor, get_processing_cursor


if __name__ == "__main__":
    # Run the same "new mail only" flow as the Process Gmail button.
    settings = get_settings()
    run_started_at = utc_now_iso()
    since = get_processing_cursor()
    result = email_research_graph.invoke(
        {
            "gmail_query": settings.gmail_query,
            "max_results": settings.gmail_max_results,
            "since": since,
        }
    )
    advance_processing_cursor(run_started_at)
    print(result)
