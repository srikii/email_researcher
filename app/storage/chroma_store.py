from __future__ import annotations

import uuid

import chromadb
from langchain_openai import OpenAIEmbeddings

from app.config import get_settings
from app.models import EmailSummary, ExtractedDocument


COLLECTION_NAME = "email_research"


def get_collection():
    # Chroma stores vectors on disk so they survive app restarts.
    settings = get_settings()
    client = chromadb.PersistentClient(path=settings.chroma_path)
    return client.get_or_create_collection(COLLECTION_NAME)


def add_email_to_vector_store(summary: EmailSummary, documents: list[ExtractedDocument]) -> list[str]:
    # Store one vector for the summary and one vector for each extracted source.
    settings = get_settings()
    embeddings = OpenAIEmbeddings(model=settings.openai_embedding_model)
    collection = get_collection()

    records = []

    key_points_text = ""
    for point in summary.key_points:
        if key_points_text:
            key_points_text += "; "
        key_points_text += point

    summary_text = (
        f"Subject: {summary.subject}\nFrom: {summary.sender}\nDate: {summary.date}\n"
        f"Received at: {summary.received_at}\n"
        f"Summary: {summary.short_summary}\nDetails: {summary.detailed_summary}\n"
        f"Key points: {key_points_text}"
    )
    records.append(("summary", summary_text, {"source": "summary"}))

    for document in documents:
        # Keep each document text bounded so embedding calls stay manageable.
        document_text = document.text[:16000]
        records.append(
            (
                document.source_type,
                document_text,
                {
                    "source": document.source,
                    "title": document.title,
                    "source_type": document.source_type,
                },
            )
        )

    ids: list[str] = []
    texts: list[str] = []
    for kind, text, metadata in records:
        record_id = f"{summary.email_id}-{kind}-{uuid.uuid4().hex[:10]}"
        ids.append(record_id)
        texts.append(text)

    vectors = embeddings.embed_documents(texts)

    metadatas = []
    for kind, _, metadata in records:
        metadatas.append(
            {
                **metadata,
                "kind": kind,
                "email_id": summary.email_id,
                "subject": summary.subject,
                "sender": summary.sender,
                "date": summary.date,
                "received_at": summary.received_at,
            }
        )

    try:
        # Reprocessing the same email should replace old vectors, not duplicate them.
        collection.delete(where={"email_id": summary.email_id})
    except Exception:
        pass

    collection.add(ids=ids, documents=texts, embeddings=vectors, metadatas=metadatas)
    return ids


def semantic_search(query: str, limit: int = 5) -> list[dict]:
    # Convert the user's question into a vector, then ask Chroma for nearby items.
    settings = get_settings()
    embeddings = OpenAIEmbeddings(model=settings.openai_embedding_model)
    collection = get_collection()
    query_embedding = embeddings.embed_query(query)
    result = collection.query(query_embeddings=[query_embedding], n_results=limit)

    hits = []
    for index, doc_id in enumerate(result.get("ids", [[]])[0]):
        hits.append(
            {
                "id": doc_id,
                "text": result.get("documents", [[]])[0][index],
                "metadata": result.get("metadatas", [[]])[0][index],
                "distance": result.get("distances", [[]])[0][index],
            }
        )
    return hits
