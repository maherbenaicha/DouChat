import os
from pathlib import Path

# Configure the app for tests BEFORE importing it
os.environ["DATABASE_URL"] = os.environ.get(
    "TEST_DATABASE_URL", "postgresql+psycopg://postgres:postgres@localhost:5432/docuchat_test"
)
os.environ["EMBEDDING_PROVIDER"] = "hash"
os.environ["LLM_PROVIDER"] = "none"
os.environ["GROQ_API_KEY"] = ""
os.environ["ADMIN_EMAIL"] = "admin@test.local"
os.environ["ADMIN_PASSWORD"] = "admin-pass"
os.environ["JWT_SECRET"] = "test-secret-key-with-enough-length-1234"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import text  # noqa: E402

from app.db import Base, engine, init_db  # noqa: E402
from app.main import app, ensure_admin  # noqa: E402
from app.seed import SAMPLE_ACCESS  # noqa: E402
from app.services.llm import get_llm_client  # noqa: E402

SAMPLE_DIR = Path(__file__).resolve().parents[1] / "sample_docs"


class FakeLLM:
    """Deterministic LLM: cites passage [1] plus an invalid passage [42]."""

    name = "fake"

    def __init__(self, reply: str | None = None):
        self.calls: list[list[dict]] = []
        self.reply = reply or "Réponse basée sur le premier passage [1]. Détail inventé [42]."

    def complete(self, messages: list[dict]) -> str:
        self.calls.append(messages)
        return self.reply


@pytest.fixture(scope="session", autouse=True)
def _database():
    Base.metadata.drop_all(bind=engine)
    init_db()
    yield


@pytest.fixture(autouse=True)
def _clean_tables():
    tables = ", ".join(t.name for t in reversed(Base.metadata.sorted_tables))
    with engine.begin() as conn:
        conn.execute(text(f"TRUNCATE {tables} RESTART IDENTITY CASCADE"))
    ensure_admin()
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture
def fake_llm():
    llm = FakeLLM()
    app.dependency_overrides[get_llm_client] = lambda: llm
    return llm


def login(client: TestClient, email: str, password: str) -> dict:
    resp = client.post("/api/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


@pytest.fixture
def admin_headers(client):
    return login(client, "admin@test.local", "admin-pass")


@pytest.fixture
def seeded(client, admin_headers):
    """Demo users + all sample documents, uploaded through the API."""
    users = {
        "alice": ("alice@test.local", ["rh"]),
        "bob": ("bob@test.local", ["tech"]),
        "chloe": ("chloe@test.local", []),
    }
    headers = {"admin": admin_headers}
    for name, (email, groups) in users.items():
        r = client.post(
            "/api/admin/users",
            json={"email": email, "password": "secret123", "full_name": name, "groups": groups},
            headers=admin_headers,
        )
        assert r.status_code == 201, r.text
        headers[name] = login(client, email, "secret123")

    for path in sorted(SAMPLE_DIR.glob("*.md")):
        r = client.post(
            "/api/documents",
            files={"file": (path.name, path.read_bytes(), "text/markdown")},
            data={"allowed_groups": ",".join(SAMPLE_ACCESS[path.name])},
            headers=admin_headers,
        )
        assert r.status_code == 201, r.text
    return headers
