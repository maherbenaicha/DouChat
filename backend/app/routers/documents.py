from typing import Annotated

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from pydantic import ValidationError
from sqlalchemy import select

from app.config import get_settings
from app.deps import AdminUser, CurrentUser, DbSession
from app.models import PUBLIC_GROUP, Document
from app.schemas import DocumentOut, _normalize_groups
from app.services.ingestion import EmptyDocumentError, ingest_document
from app.services.parsing import UnsupportedFileError

router = APIRouter(prefix="/documents", tags=["documents"])


@router.get("", response_model=list[DocumentOut])
def list_documents(db: DbSession, user: CurrentUser) -> list[Document]:
    query = select(Document).order_by(Document.created_at.desc())
    if not user.is_admin:
        query = query.where(Document.allowed_groups.overlap(user.access_groups))
    return list(db.scalars(query))


@router.post("", response_model=DocumentOut, status_code=status.HTTP_201_CREATED)
def upload_document(
    db: DbSession,
    admin: AdminUser,
    file: Annotated[UploadFile, File()],
    title: Annotated[str | None, Form()] = None,
    allowed_groups: Annotated[str, Form(description="Comma-separated groups")] = PUBLIC_GROUP,
) -> Document:
    max_bytes = get_settings().max_upload_mb * 1024 * 1024
    data = file.file.read(max_bytes + 1)
    if len(data) > max_bytes:
        raise HTTPException(status.HTTP_413_CONTENT_TOO_LARGE, "File too large")

    try:
        groups = _normalize_groups(allowed_groups.split(",")) or [PUBLIC_GROUP]
    except (ValueError, ValidationError) as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc)) from exc

    try:
        return ingest_document(
            db,
            filename=file.filename or "document.txt",
            data=data,
            title=title,
            allowed_groups=groups,
            uploaded_by=admin,
        )
    except UnsupportedFileError as exc:
        raise HTTPException(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, str(exc)) from exc
    except EmptyDocumentError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc)) from exc


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(document_id: int, db: DbSession, _: AdminUser) -> None:
    doc = db.get(Document, document_id)
    if doc is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document not found")
    db.delete(doc)
    db.commit()
