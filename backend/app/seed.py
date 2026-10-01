"""Load demo users and the sample documents.

Usage:  python -m app.seed [path/to/sample_docs]
"""

import sys
from pathlib import Path

from sqlalchemy import select

from app.db import SessionLocal, init_db
from app.main import ensure_admin
from app.models import Document, User
from app.security import hash_password
from app.services.ingestion import ingest_document

DEMO_USERS = [
    ("alice@docuchat.local", "Alice Martin (RH)", ["rh"]),
    ("bob@docuchat.local", "Bob Dupont (Tech)", ["tech"]),
    ("chloe@docuchat.local", "Chloé Bernard (Stagiaire)", []),
]
DEMO_PASSWORD = "demo1234"

# filename -> groups allowed to read it
SAMPLE_ACCESS = {
    "guide-onboarding.md": ["public"],
    "politique-teletravail.md": ["public"],
    "conges-et-absences.md": ["public"],
    "grille-salaires-2026.md": ["rh"],
    "procedure-recrutement.md": ["rh"],
    "architecture-plateforme.md": ["tech"],
    "runbook-incidents.md": ["tech"],
}


def main(docs_dir: Path) -> None:
    init_db()
    ensure_admin()
    with SessionLocal() as db:
        for email, name, groups in DEMO_USERS:
            if db.scalar(select(User).where(User.email == email)) is None:
                db.add(
                    User(
                        email=email,
                        full_name=name,
                        hashed_password=hash_password(DEMO_PASSWORD),
                        role="user",
                        groups=groups,
                    )
                )
        db.commit()

        existing = set(db.scalars(select(Document.filename)))
        for path in sorted(docs_dir.glob("*")):
            if path.name in existing or path.suffix.lower() not in {".md", ".txt", ".pdf", ".docx"}:
                continue
            doc = ingest_document(
                db,
                filename=path.name,
                data=path.read_bytes(),
                title=None,
                allowed_groups=SAMPLE_ACCESS.get(path.name, ["public"]),
                uploaded_by=None,
            )
            print(f"Ingested {doc.filename}: {doc.n_chunks} chunks, groups={doc.allowed_groups}")
    print(f"Demo users: {', '.join(u[0] for u in DEMO_USERS)} (password: {DEMO_PASSWORD})")


if __name__ == "__main__":
    default = Path(__file__).resolve().parents[1] / "sample_docs"
    main(Path(sys.argv[1]) if len(sys.argv) > 1 else default)
