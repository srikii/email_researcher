from __future__ import annotations

import json

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles

from app.config import get_settings
from app.graph.workflow import email_research_graph
from app.models import ProcessRequest, SearchRequest
from app.storage.chroma_store import semantic_search
from app.storage.sqlite_store import get_summary, init_db, list_summaries

app = FastAPI(title="Email Research Agent")
app.mount("/static", StaticFiles(directory="app/static"), name="static")


@app.on_event("startup")
def startup() -> None:
    init_db()


@app.get("/")
def index():
    return FileResponse("app/static/index.html")


@app.post("/process")
def process_emails(request: ProcessRequest):
    settings = get_settings()
    state = {
        "gmail_query": request.gmail_query or settings.gmail_query,
        "max_results": request.max_results or settings.gmail_max_results,
    }
    result = email_research_graph.invoke(state)
    return {
        "emails": len(result.get("emails", [])),
        "documents": len(result.get("documents", [])),
        "summaries": len(result.get("summaries", [])),
        "saved_summary_ids": result.get("saved_summary_ids", []),
        "errors": result.get("errors", []),
    }


@app.get("/process/stream")
def process_emails_stream(gmail_query: str | None = None, max_results: int | None = None):
    settings = get_settings()
    state = {
        "gmail_query": gmail_query or settings.gmail_query,
        "max_results": max_results or settings.gmail_max_results,
    }

    def events():
        for update in email_research_graph.stream(state):
            payload = _summarize_graph_update(update)
            yield f"data: {json.dumps(payload)}\n\n"
        yield f"data: {json.dumps({'done': True})}\n\n"

    return StreamingResponse(events(), media_type="text/event-stream")


@app.get("/summaries")
def summaries(limit: int = 50):
    return list_summaries(limit=limit)


@app.get("/summaries/{email_id}")
def summary(email_id: str):
    item = get_summary(email_id)
    return item or {"error": "not found"}


@app.post("/search")
def search(request: SearchRequest):
    return {"query": request.query, "results": semantic_search(request.query, request.limit)}


def _summarize_graph_update(update: dict) -> dict:
    node, values = next(iter(update.items()))
    return {
        "node": node,
        "emails": len(values.get("emails", [])),
        "documents": len(values.get("documents", [])),
        "summaries": len(values.get("summaries", [])),
        "saved_summary_ids": values.get("saved_summary_ids", []),
        "errors": values.get("errors", []),
    }
