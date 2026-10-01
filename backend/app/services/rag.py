"""RAG orchestration: correct -> retrieve -> generate -> verify citations."""

import re
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.models import User
from app.services.llm import LLMClient, LLMError
from app.services.query_correction import correct_query
from app.services.retrieval import RetrievedChunk, retrieve

NO_ANSWER = "Je n'ai trouvé aucune information sur ce sujet dans les documents auxquels vous avez accès."

SYSTEM_PROMPT = """You are DocuChat, an internal assistant that answers employees' questions \
using ONLY the numbered context passages provided.
Rules:
- Answer in the same language as the question.
- Every factual sentence must cite its passage(s) with [n], e.g. "... 25 jours [1]."
- If the passages do not contain the answer, say you could not find it in the documents. \
Never use outside knowledge and never invent information.
- Be concise and precise."""

CITATION_RE = re.compile(r"\[(\d+)\]")
SNIPPET_LEN = 300


@dataclass
class Source:
    ref: int
    document_id: int
    document_title: str
    page: int | None
    snippet: str
    score: float

    def as_dict(self) -> dict:
        return self.__dict__.copy()


@dataclass
class RagAnswer:
    answer: str
    sources: list[Source]
    corrected_query: str | None
    grounded: bool


def _build_context(chunks: list[RetrievedChunk]) -> str:
    parts = []
    for i, c in enumerate(chunks, start=1):
        loc = f", page {c.page}" if c.page else ""
        parts.append(f"[{i}] (source: {c.document_title}{loc})\n{c.content}")
    return "\n\n".join(parts)


def _to_source(ref: int, c: RetrievedChunk) -> Source:
    snippet = c.content if len(c.content) <= SNIPPET_LEN else c.content[:SNIPPET_LEN].rsplit(" ", 1)[0] + "…"
    return Source(ref, c.document_id, c.document_title, c.page, snippet, c.semantic_score)


def filter_citations(answer: str, n_sources: int) -> tuple[str, list[int]]:
    """Remove citations pointing to non-existent passages; return the cited refs (ordered)."""
    cited: list[int] = []

    def _check(match: re.Match) -> str:
        ref = int(match.group(1))
        if 1 <= ref <= n_sources:
            if ref not in cited:
                cited.append(ref)
            return match.group(0)
        return ""

    cleaned = CITATION_RE.sub(_check, answer)
    cleaned = re.sub(r"[ \t]{2,}", " ", cleaned).strip()
    return cleaned, cited


def _extractive_answer(chunks: list[RetrievedChunk]) -> str:
    best = chunks[0]
    return (
        "Mode extractif (aucun LLM configuré) — passage le plus pertinent :\n\n"
        f"« {best.content.strip()} » [1]"
    )


def answer_question(
    db: Session,
    user: User,
    question: str,
    llm: LLMClient | None,
    history: list[dict] | None = None,
) -> RagAnswer:
    corrected = correct_query(db, user, question)
    # Query expansion: keep the original words AND add the corrected ones, so a valid word
    # that is merely absent from the vocabulary is never lost.
    search_query = f"{question} {corrected}" if corrected else question
    chunks = retrieve(db, user, search_query)

    # Guardrail: no relevant passage -> no LLM call, no hallucination
    if not chunks:
        return RagAnswer(NO_ANSWER, [], corrected, grounded=False)

    all_sources = [_to_source(i, c) for i, c in enumerate(chunks, start=1)]

    if llm is None:
        return RagAnswer(_extractive_answer(chunks), all_sources[:1], corrected, grounded=True)

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    for turn in (history or [])[-4:]:
        messages.append({"role": turn["role"], "content": turn["content"]})
    messages.append(
        {
            "role": "user",
            "content": f"Context passages:\n\n{_build_context(chunks)}\n\nQuestion: {question}",
        }
    )

    try:
        raw = llm.complete(messages)
    except LLMError:
        return RagAnswer(
            "Le service de génération est indisponible. " + _extractive_answer(chunks),
            all_sources[:1],
            corrected,
            grounded=True,
        )

    answer, cited = filter_citations(raw, len(chunks))
    # Only return the sources the model actually used (keep their original numbering)
    sources = [all_sources[r - 1] for r in cited] if cited else []
    return RagAnswer(answer, sources, corrected, grounded=bool(cited))
