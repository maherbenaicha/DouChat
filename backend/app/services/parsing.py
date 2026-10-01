"""Extract text from uploaded files, keeping page numbers when available."""

import io
from dataclasses import dataclass


@dataclass
class Page:
    number: int | None
    text: str


SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".txt", ".md"}


class UnsupportedFileError(ValueError):
    pass


def extract_pages(filename: str, data: bytes) -> list[Page]:
    name = filename.lower()
    if name.endswith(".pdf"):
        return _extract_pdf(data)
    if name.endswith(".docx"):
        return _extract_docx(data)
    if name.endswith((".txt", ".md")):
        return [Page(number=None, text=data.decode("utf-8", errors="replace"))]
    raise UnsupportedFileError(
        f"Unsupported file type: {filename}. Supported: {', '.join(sorted(SUPPORTED_EXTENSIONS))}"
    )


def _extract_pdf(data: bytes) -> list[Page]:
    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(data))
    pages = []
    for i, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        if text.strip():
            pages.append(Page(number=i, text=text))
    return pages


def _extract_docx(data: bytes) -> list[Page]:
    from docx import Document as DocxDocument

    doc = DocxDocument(io.BytesIO(data))
    text = "\n\n".join(p.text for p in doc.paragraphs if p.text.strip())
    return [Page(number=None, text=text)]
