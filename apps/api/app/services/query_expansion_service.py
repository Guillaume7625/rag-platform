"""Query expansion via LLM.

Generates alternative phrasings of the user query to improve retrieval recall.
Uses the small (cheap) model and degrades gracefully on failure.
"""
from __future__ import annotations

from app.core.config import settings
from app.core.logging import get_logger
from app.services.llm_provider import get_llm

log = get_logger(__name__)

_SYSTEM = (
    "Rewrite the following question in {n} different ways. "
    "Output only the rewritten questions, one per line, nothing else."
)


class QueryExpansionService:
    def __init__(self) -> None:
        self.llm = get_llm()

    def expand(self, query: str, n: int = 2) -> list[str]:
        if not settings.query_expansion_enabled:
            return []
        try:
            raw = self.llm.complete(
                system=_SYSTEM.format(n=n),
                user=query,
                large=False,
            )
            lines = [line.strip() for line in raw.strip().splitlines() if line.strip()]
            return lines[:n]
        except Exception as e:
            log.warning("query_expansion.failed", error=str(e))
            return []


_expander: QueryExpansionService | None = None


def get_query_expansion() -> QueryExpansionService:
    global _expander
    if _expander is None:
        _expander = QueryExpansionService()
    return _expander
