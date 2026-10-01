import re
import unicodedata

WORD_RE = re.compile(r"\w+", re.UNICODE)

# Small FR/EN stop-word list: these words carry no meaning for lexical search
STOPWORDS = {
    # fr
    "les",
    "des",
    "une",
    "est",
    "que",
    "qui",
    "quoi",
    "dans",
    "pour",
    "par",
    "sur",
    "avec",
    "pas",
    "plus",
    "son",
    "ses",
    "aux",
    "ces",
    "cette",
    "comment",
    "combien",
    "quel",
    "quelle",
    "quels",
    "quelles",
    "faut",
    "peut",
    "peux",
    "mon",
    "mes",
    "nous",
    "vous",
    "elle",
    "ils",
    "leur",
    "leurs",
    "sont",
    "être",
    "avoir",
    "fait",
    "faire",
    "entre",
    "dois",
    "doit",
    "estce",
    "lors",
    "aussi",
    "très",
    "tout",
    "tous",
    "toutes",
    # en
    "the",
    "and",
    "for",
    "are",
    "was",
    "what",
    "how",
    "many",
    "much",
    "with",
    "this",
    "that",
    "from",
    "can",
    "does",
    "should",
    "which",
    "who",
    "when",
    "where",
    "why",
    "have",
    "has",
    "our",
    "your",
    "about",
    "into",
    "there",
    "their",
    "will",
}


def tokenize(text: str) -> list[str]:
    return [w.lower() for w in WORD_RE.findall(text)]


def keywords(text: str, min_len: int = 3) -> list[str]:
    """Meaningful lowercase tokens (no stop words, no pure numbers)."""
    seen: dict[str, None] = {}
    for tok in tokenize(text):
        if len(tok) >= min_len and tok not in STOPWORDS and not tok.isdigit():
            seen.setdefault(tok, None)
    return list(seen)


def vocabulary(text: str) -> set[str]:
    return {t for t in keywords(text) if len(t) <= 100}


def strip_accents(text: str) -> str:
    """'Télétravail' -> 'teletravail' (lowercase, no diacritics)."""
    decomposed = unicodedata.normalize("NFKD", text.lower())
    return "".join(c for c in decomposed if not unicodedata.combining(c))
