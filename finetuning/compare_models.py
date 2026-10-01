"""Compare the base and fine-tuned embedding models on the labelled evaluation set.

python compare_models.py ./docuchat-embeddings
"""

import json
import re
import sys
from pathlib import Path

from sentence_transformers import SentenceTransformer, util

from generate_pairs import passages

BASE_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
ROOT = Path(__file__).resolve().parents[1]


def evaluate(model_name: str) -> tuple[float, float]:
    model = SentenceTransformer(model_name)
    corpus = list(passages(ROOT / "backend" / "sample_docs"))
    questions = json.loads((ROOT / "backend" / "eval" / "questions.json").read_text(encoding="utf-8"))
    corpus_emb = model.encode([p for _, p in corpus], convert_to_tensor=True, normalize_embeddings=True)
    q_emb = model.encode(
        [q["question"] for q in questions], convert_to_tensor=True, normalize_embeddings=True
    )
    scores = util.cos_sim(q_emb, corpus_emb)

    hit1 = mrr = 0.0
    for i, q in enumerate(questions):
        ranked_sources = []
        for idx in scores[i].argsort(descending=True).tolist():
            src = corpus[idx][0]
            if src not in ranked_sources:
                ranked_sources.append(src)
        rank = ranked_sources.index(q["expected"]) + 1
        hit1 += rank == 1
        mrr += 1 / rank
    return hit1 / len(questions), mrr / len(questions)


if __name__ == "__main__":
    for name in (BASE_MODEL, sys.argv[1]):
        h, m = evaluate(name)
        print(f"{re.sub(r'.*/', '', name):45s} Hit@1={h:.2%}  MRR={m:.3f}")
