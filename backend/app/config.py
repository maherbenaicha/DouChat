from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings, loaded from environment variables / .env file."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "DocuChat"
    database_url: str = "postgresql+psycopg://docuchat:docuchat@localhost:5432/docuchat"

    # Auth
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 8
    admin_email: str = "admin@docuchat.local"
    admin_password: str = "admin123"

    # Embeddings: "fastembed" (real multilingual model) or "hash" (offline, for tests/CI)
    embedding_provider: str = "fastembed"
    embedding_model: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    embedding_dim: int = 384

    # LLM: "groq" (OpenAI-compatible API) or "extractive" (no LLM, returns best passages)
    llm_provider: str = "groq"
    groq_api_key: str = ""
    groq_base_url: str = "https://api.groq.com/openai/v1"
    groq_model: str = "llama-3.3-70b-versatile"
    llm_temperature: float = 0.1
    llm_timeout_seconds: float = 60.0

    # Retrieval
    chunk_size: int = 600
    chunk_overlap: int = 120
    top_k: int = 5
    candidate_k: int = 20
    min_relevance: float = 0.25
    fuzzy_threshold: float = 0.45

    cors_origins: str = "http://localhost:5173,http://localhost:8080"
    max_upload_mb: int = 20


@lru_cache
def get_settings() -> Settings:
    return Settings()
