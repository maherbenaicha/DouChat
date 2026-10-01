import pytest

from app.services.chunking import chunk_pages
from app.services.parsing import Page, UnsupportedFileError, extract_pages


def test_chunks_respect_max_size_and_are_ordered():
    text = "\n\n".join(f"Paragraphe {i}. " + "mot " * 60 for i in range(20))
    chunks = chunk_pages([Page(None, text)], chunk_size=500, overlap=100)
    assert len(chunks) > 3
    assert all(len(c.content) <= 500 for c in chunks)
    assert [c.position for c in chunks] == list(range(len(chunks)))


def test_overlap_keeps_context_between_chunks():
    text = "\n\n".join(f"Phrase numéro {i} avec du contenu utile." for i in range(60))
    chunks = chunk_pages([Page(None, text)], chunk_size=300, overlap=80)
    for prev, nxt in zip(chunks, chunks[1:], strict=False):
        tail_words = prev.content.split()[-3:]
        assert any(w in nxt.content for w in tail_words)


def test_page_numbers_are_kept():
    chunks = chunk_pages([Page(1, "Texte page un."), Page(2, "Texte page deux.")], 200, 20)
    assert [c.page for c in chunks] == [1, 2]


def test_very_long_sentence_is_hard_split():
    chunks = chunk_pages([Page(None, "a" * 2000)], chunk_size=400, overlap=50)
    assert all(len(c.content) <= 400 for c in chunks)
    assert "".join(c.content for c in chunks).count("a") >= 2000


def test_invalid_overlap():
    with pytest.raises(ValueError):
        chunk_pages([Page(None, "x")], chunk_size=100, overlap=100)


def test_unsupported_file():
    with pytest.raises(UnsupportedFileError):
        extract_pages("image.png", b"...")


def test_markdown_extraction():
    pages = extract_pages("notes.md", "# Titre\n\nContenu é".encode())
    assert pages[0].text.endswith("Contenu é")
