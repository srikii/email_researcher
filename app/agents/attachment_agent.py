from __future__ import annotations

from pathlib import Path

from docx import Document
from pypdf import PdfReader

from app.graph.state import EmailResearchState
from app.models import ExtractedDocument


def attachment_agent(state: EmailResearchState) -> EmailResearchState:
    documents: list[ExtractedDocument] = []
    errors: list[str] = []

    for email in state.get("emails", []):
        for attachment in email.attachments:
            if not attachment.local_path:
                continue

            path = Path(attachment.local_path)
            try:
                text = extract_attachment_text(path)
                if text.strip():
                    documents.append(
                        ExtractedDocument(
                            source_type="attachment",
                            source=str(path),
                            title=attachment.filename,
                            text=text,
                            email_id=email.id,
                            metadata={
                                "subject": email.subject,
                                "sender": email.sender,
                                "date": email.date,
                                "mime_type": attachment.mime_type,
                            },
                        )
                    )
            except Exception as exc:
                errors.append(f"attachment_agent failed for {attachment.filename}: {exc}")

    return {"documents": documents, "errors": errors}


def extract_attachment_text(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        reader = PdfReader(str(path))
        return "\n\n".join(page.extract_text() or "" for page in reader.pages)
    if suffix in {".docx", ".doc"}:
        doc = Document(str(path))
        return "\n".join(paragraph.text for paragraph in doc.paragraphs)
    raise ValueError(f"Unsupported attachment type: {path.suffix}")
