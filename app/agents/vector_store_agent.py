from collections import defaultdict

from app.graph.state import EmailResearchState
from app.storage.chroma_store import add_email_to_vector_store


def vector_store_agent(state: EmailResearchState) -> EmailResearchState:
    documents_by_email = defaultdict(list)
    for document in state.get("documents", []):
        documents_by_email[document.email_id].append(document)

    ids: list[str] = []
    errors: list[str] = []
    for summary in state.get("summaries", []):
        try:
            ids.extend(add_email_to_vector_store(summary, documents_by_email[summary.email_id]))
        except Exception as exc:
            errors.append(f"vector_store_agent failed for {summary.email_id}: {exc}")

    return {"stored_vector_ids": ids, "errors": errors}
