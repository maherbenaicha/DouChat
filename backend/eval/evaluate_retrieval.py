"""Measure retrieval quality on a labelled question set (Hit@1, Hit@k, MRR).

Run after `python -m app.seed`:
    python -m eval.evaluate_retrieval
"""

import json
from pathlib import Path

from sqlalchemy import select

from app.config import get_settings
from app.db import SessionLocal
from app.models import User
from app.services.query_correction import correct_query
from app.services.retrieval import retrieve


def main() -> None:
    questions = json.loads((Path(__file__).parent / "questions.json").read_text(encoding="utf-8"))
    k = get_settings().top_k
    hit1 = hitk = mrr = 0.0

    with SessionLocal() as db:
        admin = db.scalar(select(User).where(User.role == "admin"))
        for q in questions:
            query = correct_query(db, admin, q["question"]) or q["question"]
            titles = [c.document_title for c in retrieve(db, admin, query, top_k=k)]
            rank = titles.index(q["expected"]) + 1 if q["expected"] in titles else None
            hit1 += rank == 1
            hitk += rank is not None
            mrr += 1 / rank if rank else 0
            mark = "OK " if rank == 1 else ("~  " if rank else "MISS")
            print(f"{mark} rank={rank}  {q['question']}")

    n = len(questions)
    print(f"\nEmbeddings: {get_settings().embedding_provider} | {n} questions")
    print(f"Hit@1 = {hit1 / n:.2%}   Hit@{k} = {hitk / n:.2%}   MRR = {mrr / n:.3f}")


if __name__ == "__main__":
    main()
