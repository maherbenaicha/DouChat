from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select, text

from app.config import get_settings
from app.db import SessionLocal, init_db
from app.models import User
from app.routers import admin, auth, chat, documents
from app.security import hash_password


def ensure_admin() -> None:
    """Create the first admin account from environment variables if no user exists."""
    s = get_settings()
    with SessionLocal() as db:
        if db.scalar(select(User).limit(1)) is None:
            db.add(
                User(
                    email=s.admin_email.lower(),
                    full_name="Administrator",
                    hashed_password=hash_password(s.admin_password),
                    role="admin",
                    groups=[],
                )
            )
            db.commit()


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    ensure_admin()
    yield


settings = get_settings()
app = FastAPI(
    title="DocuChat API",
    description="Internal RAG portal: ask questions about company documents, "
    "with sourced answers and group-based access control.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",") if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

for r in (auth.router, documents.router, chat.router, admin.router):
    app.include_router(r, prefix="/api")


@app.get("/api/health", tags=["health"])
def health() -> dict:
    with SessionLocal() as db:
        db.execute(text("SELECT 1"))
    return {"status": "ok", "llm": settings.llm_provider if settings.groq_api_key else "extractive"}
