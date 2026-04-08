"""LLM provider abstraction.

Production: Anthropic Messages API.  Small model is Haiku for standard mode,
large model is Sonnet for deep / fallback mode.

Dev fallback: returns the assembled context verbatim when no API key is set,
so the platform stays demoable without credentials.
"""
from __future__ import annotations

import httpx

from app.core.config import settings
from app.core.logging import get_logger

log = get_logger(__name__)


class LLMProvider:
    ANTHROPIC_ENDPOINT = "https://api.anthropic.com/v1/messages"
    ANTHROPIC_VERSION = "2023-06-01"

    def __init__(self) -> None:
        self.provider = settings.llm_provider
        self.small = settings.llm_small_model
        self.large = settings.llm_large_model
        self.anthropic_key = settings.anthropic_api_key
        self.openai_key = settings.openai_api_key

    def _is_configured(self) -> bool:
        if self.provider == "anthropic":
            return bool(self.anthropic_key)
        if self.provider == "openai":
            return bool(self.openai_key)
        return False

    def complete(self, system: str, user: str, large: bool = False) -> str:
        model = self.large if large else self.small
        if not self._is_configured():
            log.warning("llm.fallback_used", reason="no_api_key", provider=self.provider)
            return (
                "[dev-stub] No LLM credentials configured. Below is the raw "
                "assembled context:\n\n" + user
            )
        try:
            if self.provider == "anthropic":
                return self._call_anthropic(system, user, model)
            if self.provider == "openai":
                return self._call_openai(system, user, model)
            return f"[llm-error] Unknown provider: {self.provider}"
        except Exception as e:
            log.error("llm.call_failed", error=str(e), model=model, provider=self.provider)
            return "[llm-error] The generation step failed. Please retry."

    def _call_anthropic(self, system: str, user: str, model: str) -> str:
        resp = httpx.post(
            self.ANTHROPIC_ENDPOINT,
            headers={
                "x-api-key": self.anthropic_key,
                "anthropic-version": self.ANTHROPIC_VERSION,
                "content-type": "application/json",
            },
            json={
                "model": model,
                "max_tokens": 2048,
                "system": system,
                "messages": [{"role": "user", "content": user}],
                "temperature": 0.1,
            },
            timeout=120.0,
        )
        resp.raise_for_status()
        data = resp.json()
        return "".join(
            block.get("text", "")
            for block in data.get("content", [])
            if block.get("type") == "text"
        )

    def _call_openai(self, system: str, user: str, model: str) -> str:
        resp = httpx.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {self.openai_key}"},
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                "temperature": 0.1,
            },
            timeout=120.0,
        )
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]


_provider: LLMProvider | None = None


def get_llm() -> LLMProvider:
    global _provider
    if _provider is None:
        _provider = LLMProvider()
    return _provider
