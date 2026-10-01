"""Typo-tolerant queries.

Each unknown word of the question is matched (trigram similarity, pg_trgm) against
the vocabulary of the documents *the user is allowed to read*. Matching is done on
accent-free forms, so it fixes typos such as "teletravial" -> "télétravail" or
"indemnite" -> "indemnité", without ever suggesting words from restricted documents.
"""

import re

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import User
from app.services.text_utils import STOPWORDS, WORD_RE, strip_accents

ACCESS_FILTER = "(:is_admin OR d.allowed_groups && CAST(:groups AS varchar[]))"

_EXISTS_SQL = text(
    f"""
    SELECT 1 FROM document_terms t JOIN documents d ON d.id = t.document_id
    WHERE t.term = :tok AND {ACCESS_FILTER}
    LIMIT 1
    """
)

_SUGGEST_SQL = text(
    f"""
    SELECT t.term, similarity(t.term_key, :key) AS sim
    FROM document_terms t JOIN documents d ON d.id = t.document_id
    WHERE t.term_key % :key AND {ACCESS_FILTER}
    ORDER BY sim DESC, t.term
    LIMIT 1
    """
)


def access_params(user: User) -> dict:
    return {"is_admin": user.is_admin, "groups": user.access_groups}


def correct_query(db: Session, user: User, query: str) -> str | None:
    """Return the corrected query, or None when nothing was changed."""
    threshold = get_settings().fuzzy_threshold
    params = access_params(user)
    replacements: dict[str, str] = {}

    for tok in {w.lower() for w in WORD_RE.findall(query)}:
        if len(tok) < 4 or tok in STOPWORDS or tok.isdigit():
            continue
        if db.execute(_EXISTS_SQL, {"tok": tok, **params}).first():
            continue
        row = db.execute(_SUGGEST_SQL, {"key": strip_accents(tok), **params}).first()
        if row and row.sim >= threshold and row.term != tok:
            replacements[tok] = row.term

    if not replacements:
        return None

    def _sub(match: re.Match) -> str:
        return replacements.get(match.group(0).lower(), match.group(0))

    return WORD_RE.sub(_sub, query)
