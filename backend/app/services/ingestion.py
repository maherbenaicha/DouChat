from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import Chunk, Document, DocumentTerm, User
from app.services.chunking import chunk_pages
from app.services.embeddings import get_embedding_provider
from app.services.parsing import extract_pages
from app.services.text_utils import strip_accents, vocabulary

CONTENT_TYPES = {
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".md": "text/markdown",
    ".txt": "text/plain",
}

EMBED_BATCH = 32


class EmptyDocumentError(ValueError):
    pass


def ingest_document(
    db: Session,
    *,
    filename: str,
    data: bytes,
    title: str | None,
    allowed_groups: list[str],
    uploaded_by: User | None,
) -> Document:
    settings = get_settings()
    pages = extract_pages(filename, data)
    chunks = chunk_pages(pages, settings.chunk_size, settings.chunk_overlap)
    if not chunks:
        raise EmptyDocumentError("No text could be extracted from this file.")

    provider = get_embedding_provider()
    vectors: list[list[float]] = []
    for i in range(0, len(chunks), EMBED_BATCH):
        vectors.extend(provider.embed([c.content for c in chunks[i : i + EMBED_BATCH]]))

    ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    doc = Document(
        title=(title or filename.rsplit(".", 1)[0]).strip()[:255],
        filename=filename[:255],
        content_type=CONTENT_TYPES.get(ext, "application/octet-stream"),
        allowed_groups=allowed_groups,
        uploaded_by_id=uploaded_by.id if uploaded_by else None,
        n_chunks=len(chunks),
    )
    doc.chunks = [
        Chunk(position=c.position, page=c.page, content=c.content, embedding=v)
        for c, v in zip(chunks, vectors, strict=True)
    ]
    db.add(doc)
    db.flush()

    terms = set()
    for c in chunks:
        terms |= vocabulary(c.content)
    db.add_all(DocumentTerm(document_id=doc.id, term=t, term_key=strip_accents(t)) for t in terms)
    db.commit()
    db.refresh(doc)
    return doc
