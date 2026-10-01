"""Generate synthetic (question, passage) training pairs from internal documents with an LLM.

GROQ_API_KEY=... python generate_pairs.py ../backend/sample_docs pairs.jsonl
"""

import json
import os
import re
import sys
from pathlib import Path

import httpx

PROMPT = """Voici un extrait d'un document interne d'entreprise.
Écris 3 questions variées et réalistes qu'un employé pourrait poser et dont la réponse
se trouve dans cet extrait. Une question par ligne, sans numérotation.

Extrait :
{passage}"""


def passages(folder: Path, max_chars: int = 800):
    for path in sorted(folder.glob("*.md")):
        for block in re.split(r"\n(?=## )", path.read_text(encoding="utf-8")):
            block = block.strip()
            if len(block) > 80:
                yield path.stem, block[:max_chars]


def ask(passage: str) -> list[str]:
    resp = httpx.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={"Authorization": f"Bearer {os.environ['GROQ_API_KEY']}"},
        json={
            "model": "llama-3.3-70b-versatile",
            "temperature": 0.7,
            "messages": [{"role": "user", "content": PROMPT.format(passage=passage)}],
        },
        timeout=60,
    )
    resp.raise_for_status()
    text = resp.json()["choices"][0]["message"]["content"]
    return [q.strip("-• ").strip() for q in text.splitlines() if q.strip().endswith("?")]


def main(folder: Path, out: Path) -> None:
    n = 0
    with out.open("w", encoding="utf-8") as f:
        for source, passage in passages(folder):
            for question in ask(passage):
                f.write(
                    json.dumps(
                        {"anchor": question, "positive": passage, "source": source}, ensure_ascii=False
                    )
                    + "\n"
                )
                n += 1
    print(f"Wrote {n} pairs to {out}")


if __name__ == "__main__":
    main(Path(sys.argv[1]), Path(sys.argv[2]))
