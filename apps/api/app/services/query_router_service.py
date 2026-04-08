"""Routes a query to `standard` or `deep` mode."""
from __future__ import annotations

import re

_DEEP_TRIGGERS = re.compile(
    r"\b(compare|compar[ée]|diff[ée]rence|vs|versus|synth[èe]se|r[ée]capitule|"
    r"across|toutes les|all the|summari[sz]e all|multi.?doc|transverse)\b",
    re.IGNORECASE,
)


def decide_mode(query: str, forced: str | None = None) -> str:
    if forced in {"standard", "deep"}:
        return forced
    if _DEEP_TRIGGERS.search(query):
        return "deep"
    if query.count("?") > 1:
        return "deep"
    if len(query.split()) > 40:
        return "deep"
    return "standard"


def decompose(query: str, max_sub: int = 4) -> list[str]:
    """Very light query decomposition for deep mode.

    Splits on 'et', 'and', ';', newlines, or clause boundaries.  Replace with
    an LLM-based decomposer for richer behavior.
    """
    parts = re.split(r"\s*(?:;|\n| et | and | puis )\s*", query)
    parts = [p.strip(" .?!") for p in parts if p.strip()]
    if len(parts) <= 1:
        return [query]
    return parts[:max_sub]
