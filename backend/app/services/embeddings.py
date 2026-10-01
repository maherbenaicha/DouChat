"""Embedding providers.

- FastEmbedProvider: local ONNX multilingual model (no GPU, no paid API).
- HashEmbeddingProvider: deterministic character-trigram hashing. Fully offline,
  used in tests and CI so the pipeline can run without downloading a model.
"""

import hashlib
import math
import re
from functools import lru_cache
from typing import Protocol

from app.config import get_settings


class EmbeddingProvider(Protocol):
    dim: int

    def embed(self, texts: list[str]) -> list[list[float]]: ...


class FastEmbedProvider:
    def __init__(self, model_name: str, dim: int):
        from fastembed import TextEmbedding

        self.model = TextEmbedding(model_name)
        self.dim = dim

    def embed(self, texts: list[str]) -> list[list[float]]:
        vectors = [v.tolist() for v in self.model.embed(texts)]
        if vectors and len(vectors[0]) != self.dim:
            raise ValueError(f"Model returns {len(vectors[0])}-d vectors but EMBEDDING_DIM={self.dim}")
        return vectors


class HashEmbeddingProvider:
    def __init__(self, dim: int):
        self.dim = dim

    def _vector(self, text: str) -> list[float]:
        vec = [0.0] * self.dim
        words = re.findall(r"\w+", text.lower())
        for word in words:
            padded = f"#{word}#"
            for i in range(len(padded) - 2):
                h = int(hashlib.md5(padded[i : i + 3].encode()).hexdigest(), 16)
                vec[h % self.dim] += 1.0
        norm = math.sqrt(sum(x * x for x in vec)) or 1.0
        return [x / norm for x in vec]

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._vector(t) for t in texts]


@lru_cache
def get_embedding_provider() -> EmbeddingProvider:
    s = get_settings()
    if s.embedding_provider == "hash":
        return HashEmbeddingProvider(s.embedding_dim)
    if s.embedding_provider == "fastembed":
        return FastEmbedProvider(s.embedding_model, s.embedding_dim)
    raise ValueError(f"Unknown EMBEDDING_PROVIDER: {s.embedding_provider}")
