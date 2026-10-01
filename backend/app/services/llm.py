"""LLM clients. Groq exposes an OpenAI-compatible API, so switching to OpenAI,
Mistral or a local vLLM/Ollama server only requires changing the base URL."""

from functools import lru_cache
from typing import Protocol

import httpx

from app.config import get_settings


class LLMError(RuntimeError):
    pass


class LLMClient(Protocol):
    name: str

    def complete(self, messages: list[dict]) -> str: ...


class OpenAICompatibleClient:
    def __init__(self, base_url: str, api_key: str, model: str, temperature: float, timeout: float):
        self.name = model
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.temperature = temperature
        self.timeout = timeout

    def complete(self, messages: list[dict]) -> str:
        try:
            resp = httpx.post(
                f"{self.base_url}/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={
                    "model": self.model,
                    "messages": messages,
                    "temperature": self.temperature,
                },
                timeout=self.timeout,
            )
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"].strip()
        except (httpx.HTTPError, KeyError, IndexError) as exc:
            raise LLMError(f"LLM request failed: {exc}") from exc


@lru_cache
def get_llm_client() -> LLMClient | None:
    """Return the configured LLM, or None for extractive mode (no generation)."""
    s = get_settings()
    if s.llm_provider == "groq" and s.groq_api_key:
        return OpenAICompatibleClient(
            s.groq_base_url, s.groq_api_key, s.groq_model, s.llm_temperature, s.llm_timeout_seconds
        )
    return None
