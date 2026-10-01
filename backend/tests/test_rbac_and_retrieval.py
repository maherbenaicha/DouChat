"""Access control is the most important guarantee of the portal:
a user must never see, retrieve, or be suggested content from a restricted document."""

from app.db import SessionLocal
from app.models import User
from app.services.query_correction import correct_query
from app.services.retrieval import retrieve


def _titles(client, headers):
    return {d["filename"] for d in client.get("/api/documents", headers=headers).json()}


def _user(email):
    with SessionLocal() as db:
        return db.query(User).filter_by(email=email).one()


def test_document_listing_is_filtered_by_group(client, seeded):
    public = {"guide-onboarding.md", "politique-teletravail.md", "conges-et-absences.md"}
    assert _titles(client, seeded["chloe"]) == public
    assert _titles(client, seeded["alice"]) == public | {
        "grille-salaires-2026.md",
        "procedure-recrutement.md",
    }
    assert _titles(client, seeded["bob"]) == public | {
        "architecture-plateforme.md",
        "runbook-incidents.md",
    }
    assert len(_titles(client, seeded["admin"])) == 7


def test_retrieval_never_returns_restricted_chunks(seeded):
    question = "grille de salaires ingénieur junior gratification stagiaire"
    with SessionLocal() as db:
        chloe_hits = retrieve(db, _user("chloe@test.local"), question)
        alice_hits = retrieve(db, _user("alice@test.local"), question)
    assert all(h.document_title != "grille-salaires-2026" for h in chloe_hits)
    assert alice_hits[0].document_title == "grille-salaires-2026"


def test_relevant_document_ranks_first(seeded):
    with SessionLocal() as db:
        hits = retrieve(db, _user("chloe@test.local"), "combien de jours de télétravail par semaine")
    assert hits[0].document_title == "politique-teletravail"


def test_typo_is_corrected(seeded):
    with SessionLocal() as db:
        corrected = correct_query(db, _user("chloe@test.local"), "indemnite de teletravial ?")
    assert corrected is not None
    assert "télétravail" in corrected


def test_query_correction_does_not_leak_restricted_vocabulary(seeded):
    # "astreinte" only exists in the tech runbook
    with SessionLocal() as db:
        for_chloe = correct_query(db, _user("chloe@test.local"), "astreintte")
        for_bob = correct_query(db, _user("bob@test.local"), "astreintte")
    assert for_chloe is None or "astreinte" not in for_chloe
    assert for_bob == "astreinte"


def test_deleting_document_removes_its_chunks(client, seeded):
    docs = client.get("/api/documents", headers=seeded["admin"]).json()
    target = next(d for d in docs if d["filename"] == "runbook-incidents.md")
    assert client.delete(f"/api/documents/{target['id']}", headers=seeded["admin"]).status_code == 204
    with SessionLocal() as db:
        hits = retrieve(db, _user("bob@test.local"), "astreinte incident SEV1")
    assert all(h.document_id != target["id"] for h in hits)
