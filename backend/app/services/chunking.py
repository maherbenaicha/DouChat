"""Split documents into overlapping chunks, preferring paragraph and sentence boundaries."""

import re
from dataclasses import dataclass

from app.services.parsing import Page


@dataclass
class TextChunk:
    content: str
    page: int | None
    position: int


_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")


def _normalize(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _split_units(text: str, max_chars: int) -> list[str]:
    """Paragraphs, further split into sentences (then hard-cut) when too long."""
    units: list[str] = []
    for para in re.split(r"\n\s*\n", text):
        para = para.strip()
        if not para:
            continue
        if len(para) <= max_chars:
            units.append(para)
            continue
        for sentence in _SENTENCE_SPLIT.split(para):
            while len(sentence) > max_chars:
                units.append(sentence[:max_chars])
                sentence = sentence[max_chars:]
            if sentence.strip():
                units.append(sentence.strip())
    return units


def chunk_pages(pages: list[Page], chunk_size: int = 800, overlap: int = 150) -> list[TextChunk]:
    if overlap >= chunk_size:
        raise ValueError("overlap must be smaller than chunk_size")

    chunks: list[TextChunk] = []
    for page in pages:
        units = _split_units(_normalize(page.text), chunk_size)
        current = ""
        for unit in units:
            candidate = f"{current}\n\n{unit}" if current else unit
            if len(candidate) <= chunk_size:
                current = candidate
                continue
            chunks.append(TextChunk(current, page.number, len(chunks)))
            # Carry the end of the previous chunk to keep context across boundaries
            tail = current[-overlap:] if overlap else ""
            if tail and " " in tail:
                tail = tail[tail.index(" ") + 1 :]
            current = f"{tail} {unit}".strip() if tail else unit
            if len(current) > chunk_size:
                current = unit
        if current.strip():
            chunks.append(TextChunk(current, page.number, len(chunks)))
    return chunks
