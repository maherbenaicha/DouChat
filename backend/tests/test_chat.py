from app.services.rag import NO_ANSWER, filter_citations
from tests.conftest import FakeLLM


def test_filter_citations_removes_invalid_refs():
    text, cited = filter_citations("A [1]. B [3][1]. C [9].", n_sources=3)
    assert "[9]" not in text
    assert cited == [1, 3]


def test_chat_returns_answer_with_only_cited_sources(client, seeded, fake_llm):
    r = client.post(
        "/api/chat",
        json={"question": "Combien de jours de congés payés par an ?"},
        headers=seeded["chloe"],
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert "[42]" not in body["answer"]  # hallucinated citation removed
    assert body["grounded"] is True
    assert [s["ref"] for s in body["sources"]] == [1]
    assert body["sources"][0]["document_title"] == "conges-et-absences"

    # The prompt sent to the LLM contains the numbered context
    prompt = fake_llm.calls[0][-1]["content"]
    assert "[1] (source: conges-et-absences)" in prompt


def test_no_relevant_context_means_no_llm_call(client, seeded, fake_llm):
    r = client.post(
        "/api/chat",
        json={"question": "xyzzy qwerty zzzz"},
        headers=seeded["chloe"],
    )
    body = r.json()
    assert body["answer"] == NO_ANSWER
    assert body["sources"] == []
    assert fake_llm.calls == []


def test_restricted_content_never_reaches_the_llm(client, seeded, fake_llm):
    client.post(
        "/api/chat",
        json={"question": "Quel est le salaire d'un ingénieur junior ?"},
        headers=seeded["chloe"],
    )
    for call in fake_llm.calls:
        assert "42 000" not in call[-1]["content"]


def test_extractive_mode_without_llm(client, seeded):
    r = client.post(
        "/api/chat",
        json={"question": "jours de télétravail par semaine"},
        headers=seeded["chloe"],
    )
    body = r.json()
    assert body["answer"].startswith("Mode extractif")
    assert body["sources"][0]["document_title"] == "politique-teletravail"


def test_conversation_history_and_isolation(client, seeded):
    from app.main import app
    from app.services.llm import get_llm_client

    llm = FakeLLM("Deux jours par semaine [1].")
    app.dependency_overrides[get_llm_client] = lambda: llm

    first = client.post(
        "/api/chat", json={"question": "Télétravail : combien de jours ?"}, headers=seeded["chloe"]
    ).json()
    conv_id = first["conversation_id"]
    client.post(
        "/api/chat",
        json={"question": "Et l'indemnité ?", "conversation_id": conv_id},
        headers=seeded["chloe"],
    )
    # Second call includes the previous turn as history
    assert any(m["content"] == "Télétravail : combien de jours ?" for m in llm.calls[1])

    msgs = client.get(f"/api/conversations/{conv_id}/messages", headers=seeded["chloe"]).json()
    assert [m["role"] for m in msgs] == ["user", "assistant", "user", "assistant"]

    # Another user cannot read or continue this conversation
    assert client.get(f"/api/conversations/{conv_id}/messages", headers=seeded["bob"]).status_code == 404
    r = client.post(
        "/api/chat", json={"question": "hello", "conversation_id": conv_id}, headers=seeded["bob"]
    )
    assert r.status_code == 404
