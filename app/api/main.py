from __future__ import annotations

import json

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles

from app.config import get_settings
from app.graph.workflow import email_research_graph
from app.models import ProcessRequest, SearchRequest
from app.services.time_utils import utc_now_iso
from app.storage.chroma_store import semantic_search
from app.storage.sqlite_store import (
    advance_processing_cursor,
    get_processing_cursor,
    get_summary,
    init_db,
    list_summaries,
)

app = FastAPI(title="Email Research Agent")

# Serve files from app/static so the simple web UI works without a separate frontend.
app.mount("/static", StaticFiles(directory="app/static"), name="static")


@app.on_event("startup")
def startup() -> None:
    # Make sure SQLite tables exist before requests start coming in.
    init_db()


@app.get("/")
def index():
    # Return the browser UI.
    return FileResponse("app/static/index.html")


@app.post("/process")
def process_emails(request: ProcessRequest):
    # Non-streaming version of processing. Useful for scripts or API clients.
    settings = get_settings()

    # Save the run start time. If this is normal "new mail" processing, the
    # cursor advances to this value after the run finishes.
    run_started_at = utc_now_iso()

    # If the user did not provide a manual start time, use the saved cursor.
    since = request.since or get_processing_cursor()
    state = {
        "gmail_query": request.gmail_query or settings.gmail_query,
        "max_results": request.max_results or settings.gmail_max_results,
        "since": since,
        "until": request.until,
    }
    result = email_research_graph.invoke(state)

    # Only advance the cursor for normal processing. Manual date ranges should
    # not change where future "new mail" runs begin.
    if request.since is None and request.until is None:
        advance_processing_cursor(run_started_at)
    return {
        "since": since,
        "until": request.until,
        "emails": len(result.get("emails", [])),
        "documents": len(result.get("documents", [])),
        "summaries": len(result.get("summaries", [])),
        "saved_summary_ids": result.get("saved_summary_ids", []),
        "errors": result.get("errors", []),
    }


@app.get("/process/stream")
def process_emails_stream(
    gmail_query: str | None = None,
    max_results: int | None = None,
    since: str | None = None,
    until: str | None = None,
):
    # Streaming version used by the web UI. It sends progress after each graph node.
    settings = get_settings()
    run_started_at = utc_now_iso()
    effective_since = since or get_processing_cursor()
    state = {
        "gmail_query": gmail_query or settings.gmail_query,
        "max_results": max_results or settings.gmail_max_results,
        "since": effective_since,
        "until": until,
    }

    def events():
        # Server-Sent Events send text lines beginning with "data:".
        yield f"data: {json.dumps({'node': 'cursor', 'since': effective_since, 'until': until})}\n\n"

        for update in email_research_graph.stream(state):
            payload = _summarize_graph_update(update)
            yield f"data: {json.dumps(payload)}\n\n"

        if since is None and until is None:
            advance_processing_cursor(run_started_at)

        yield f"data: {json.dumps({'done': True})}\n\n"

    return StreamingResponse(events(), media_type="text/event-stream")


@app.get("/summaries")
def summaries(limit: int = 50, since: str | None = None, until: str | None = None):
    # List summaries, optionally inside a user-selected time range.
    return list_summaries(limit=limit, since=since, until=until)


@app.get("/summaries/{email_id}")
def summary(email_id: str):
    # Fetch a single summary by Gmail message ID.
    item = get_summary(email_id)
    return item or {"error": "not found"}


@app.post("/search")
def search(request: SearchRequest):
    # Semantic search over Chroma vectors.
    return {"query": request.query, "results": semantic_search(request.query, request.limit)}


def _summarize_graph_update(update: dict) -> dict:
    # LangGraph stream updates look like {"node_name": {"changed": "state"}}.
    # This converts that into a smaller object for the frontend status line.
    node, values = next(iter(update.items()))
    return {
        "node": node,
        "emails": len(values.get("emails", [])),
        "documents": len(values.get("documents", [])),
        "summaries": len(values.get("summaries", [])),
        "saved_summary_ids": values.get("saved_summary_ids", []),
        "errors": values.get("errors", []),
    }
