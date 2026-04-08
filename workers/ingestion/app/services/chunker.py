"""Parent / child chunking.

Token counts are approximated by whitespace words * 1.3 to avoid shipping a
tokenizer in the worker.  Swap with tiktoken or the BGE tokenizer in prod.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from app.config import settings
from app.services.parser import ParsedSection


@dataclass
class ParentChunk:
    order: int
    page: int | None
    section_title: str | None
    content: str
    token_count: int
    children: list[ChildChunk] = field(default_factory=list)


@dataclass
class ChildChunk:
    order: int
    content: str
    token_count: int


def _tok(text: str) -> int:
    # Rough approximation.
    return int(len(text.split()) * 1.3)


def _split_by_tokens(text: str, target_tokens: int, overlap_tokens: int = 0) -> list[str]:
    words = text.split()
    if not words:
        return []
    approx_words_per_chunk = max(1, int(target_tokens / 1.3))
    overlap_words = max(0, int(overlap_tokens / 1.3))
    out: list[str] = []
    i = 0
    while i < len(words):
        chunk_words = words[i : i + approx_words_per_chunk]
        out.append(" ".join(chunk_words))
        if i + approx_words_per_chunk >= len(words):
            break
        i += max(1, approx_words_per_chunk - overlap_words)
    return out


def chunk_sections(sections: list[ParsedSection]) -> list[ParentChunk]:
    parents: list[ParentChunk] = []
    parent_order = 0
    for section in sections:
        parent_texts = _split_by_tokens(section.text, settings.chunk_parent_tokens)
        for pt in parent_texts:
            children_texts = _split_by_tokens(
                pt,
                target_tokens=settings.chunk_child_tokens,
                overlap_tokens=settings.chunk_child_overlap,
            )
            children = [
                ChildChunk(order=ci, content=ct, token_count=_tok(ct))
                for ci, ct in enumerate(children_texts)
            ]
            parents.append(
                ParentChunk(
                    order=parent_order,
                    page=section.page,
                    section_title=section.section_title,
                    content=pt,
                    token_count=_tok(pt),
                    children=children,
                )
            )
            parent_order += 1
    return parents
