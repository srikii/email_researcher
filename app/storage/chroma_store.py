from __future__ import annotations

import uuid

import chromadb
from langchain_openai import OpenAIEmbeddings

from app.config import get_settings
from app.models import EmailSummary, ExtractedDocument


COLLECTION_NAME = "email_research"


def get_collection():
    settings = get_settings()
    client = chromadb.PersistentClient(path=settings.chroma_path)
    return client.get_or_create_collection(COLLECTION_NAME)


def add_email_to_vector_store(summary: EmailSummary, documents: list[ExtractedDocument]) -> list[str]:
    settings = get_settings()
    embeddings = OpenAIEmbeddings(model=settings.openai_embedding_model)
    collection = get_collection()

    records = []
    summary_text = (
        f"Subject: {summary.subject}\nFrom: {summary.sender}\nDate: {summary.date}\n"
        f"Summary: {summary.short_summary}\nDetails: {summary.detailed_summary}\n"
        f"Key points: {'; '.join(summary.key_points)}"
    )
    records.append(("summary", summary_text, {"source": "summary"}))

    for document in documents:
        records.append(
            (
                document.source_type,
                document.text[:16000],
                {
                    "source": document.source,
                    "title": document.title,
                    "source_type": document.source_type,
                },
            )
        )

    ids = [f"{summary.email_id}-{kind}-{uuid.uuid4().hex[:10]}" for kind, _, _ in records]
    texts = [text for _, text, _ in records]
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
            }
        )

    collection.add(ids=ids, documents=texts, embeddings=vectors, metadatas=metadatas)
    return ids


def semantic_search(query: str, limit: int = 5) -> list[dict]:
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
