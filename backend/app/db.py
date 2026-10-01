from collections.abc import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import get_settings


class Base(DeclarativeBase):
    pass


engine = create_engine(get_settings().database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Create extensions, tables and search indexes (idempotent)."""
    from app import models  # noqa: F401  (registers the models on Base)

    with engine.begin() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm"))

    Base.metadata.create_all(bind=engine)

    with engine.begin() as conn:
        # Approximate nearest-neighbour index for semantic search (cosine distance)
        conn.execute(
            text(
                "CREATE INDEX IF NOT EXISTS ix_chunks_embedding_hnsw "
                "ON chunks USING hnsw (embedding vector_cosine_ops)"
            )
        )
        # Trigram indexes for typo-tolerant lexical search and query correction
        conn.execute(
            text(
                "CREATE INDEX IF NOT EXISTS ix_chunks_content_trgm ON chunks USING gin (content gin_trgm_ops)"
            )
        )
        conn.execute(
            text(
                "CREATE INDEX IF NOT EXISTS ix_document_terms_term_trgm "
                "ON document_terms USING gin (term_key gin_trgm_ops)"
            )
        )
