"""Hybrid retrieval: semantic (pgvector) + lexical (PostgreSQL full-text), fused with
Reciprocal Rank Fusion. Access control is enforced *inside the SQL query*, so a user
can never retrieve a chunk from a document outside their groups."""

from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import User
from app.services.embeddings import get_embedding_provider
from app.services.query_correction import ACCESS_FILTER, access_params
from app.services.text_utils import keywords

RRF_K = 60

_VECTOR_SQL = text(
    f"""
    SELECT c.id, 1 - (c.embedding <=> CAST(:emb AS vector)) AS score
    FROM chunks c JOIN documents d ON d.id = c.document_id
    WHERE {ACCESS_FILTER}
    ORDER BY c.embedding <=> CAST(:emb AS vector)
    LIMIT :k
    """
)

_LEXICAL_SQL = text(
    f"""
    SELECT c.id, ts_rank_cd(to_tsvector('simple', c.content), to_tsquery('simple', :tsq)) AS score
    FROM chunks c JOIN documents d ON d.id = c.document_id
    WHERE {ACCESS_FILTER}
      AND to_tsvector('simple', c.content) @@ to_tsquery('simple', :tsq)
    ORDER BY score DESC
    LIMIT :k
    """
)

_FETCH_SQL = text(
    """
    SELECT c.id, c.content, c.page, c.document_id, d.title
    FROM chunks c JOIN documents d ON d.id = c.document_id
    WHERE c.id = ANY(:ids)
    """
)


@dataclass
class RetrievedChunk:
    chunk_id: int
    document_id: int
    document_title: str
    page: int | None
    content: str
    semantic_score: float
    lexical_score: float
    fused_score: float


def _to_tsquery(query: str) -> str | None:
    terms = [t.replace("'", "") for t in keywords(query)]
    terms = [t for t in terms if t]
    # prefix match (term:*) so "congé" also matches "congés"
    return " | ".join(f"{t}:*" for t in terms) if terms else None


def retrieve(db: Session, user: User, query: str, top_k: int | None = None) -> list[RetrievedChunk]:
    settings = get_settings()
    top_k = top_k or settings.top_k
    params = access_params(user)

    embedding = get_embedding_provider().embed([query])[0]
    emb_literal = "[" + ",".join(f"{x:.6f}" for x in embedding) + "]"
    semantic = {
        row.id: float(row.score)
        for row in db.execute(_VECTOR_SQL, {"emb": emb_literal, "k": settings.candidate_k, **params})
    }

    lexical: dict[int, float] = {}
    tsq = _to_tsquery(query)
    if tsq:
        lexical = {
            row.id: float(row.score)
            for row in db.execute(_LEXICAL_SQL, {"tsq": tsq, "k": settings.candidate_k, **params})
        }

    # Reciprocal Rank Fusion
    fused: dict[int, float] = {}
    for ranking in (semantic, lexical):
        ordered = sorted(ranking, key=ranking.get, reverse=True)
        for rank, chunk_id in enumerate(ordered, start=1):
            fused[chunk_id] = fused.get(chunk_id, 0.0) + 1.0 / (RRF_K + rank)

    # Drop chunks that are neither semantically close nor lexically matching
    candidates = [cid for cid in fused if cid in lexical or semantic.get(cid, 0.0) >= settings.min_relevance]
    candidates.sort(key=lambda cid: fused[cid], reverse=True)
    candidates = candidates[:top_k]
    if not candidates:
        return []

    rows = {row.id: row for row in db.execute(_FETCH_SQL, {"ids": candidates})}
    return [
        RetrievedChunk(
            chunk_id=cid,
            document_id=rows[cid].document_id,
            document_title=rows[cid].title,
            page=rows[cid].page,
            content=rows[cid].content,
            semantic_score=round(semantic.get(cid, 0.0), 4),
            lexical_score=round(lexical.get(cid, 0.0), 4),
            fused_score=round(fused[cid], 5),
        )
        for cid in candidates
        if cid in rows
    ]
