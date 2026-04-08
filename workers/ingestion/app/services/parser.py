"""Document parser.

Primary: Docling for structured parsing (PDF, DOCX, PPTX, HTML, MD).
Fallback: plain UTF-8 decode for text-like formats.
OCR fallback for scanned PDFs is left as a TODO hook.
"""
from __future__ import annotations

import io
from dataclasses import dataclass


@dataclass
class ParsedSection:
    order: int
    page: int | None
    section_title: str | None
    text: str


def parse_document(content: bytes, mime_type: str, filename: str) -> list[ParsedSection]:
    # Try Docling for rich formats.
    if mime_type in {
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        "text/html",
    }:
        try:
            from docling.document_converter import DocumentConverter  # type: ignore

            converter = DocumentConverter()
            result = converter.convert(io.BytesIO(content))
            md = result.document.export_to_markdown()
            return _split_markdown(md)
        except Exception:
            # Fall through to plain-text handling.
            pass

    if mime_type.startswith("text/") or mime_type in {
        "application/json",
        "application/xml",
        "text/csv",
    }:
        text = content.decode("utf-8", errors="replace")
        return _split_markdown(text)

    # Last-resort: decode with replacement.
    text = content.decode("utf-8", errors="replace")
    return _split_markdown(text)


def _split_markdown(text: str) -> list[ParsedSection]:
    """Split on markdown headings into coarse sections."""
    sections: list[ParsedSection] = []
    current_title: str | None = None
    current_lines: list[str] = []
    order = 0

    def flush() -> None:
        nonlocal order
        body = "\n".join(current_lines).strip()
        if body:
            sections.append(
                ParsedSection(order=order, page=None, section_title=current_title, text=body)
            )
            order += 1

    for line in text.splitlines():
        if line.startswith("#"):
            flush()
            current_title = line.lstrip("# ").strip() or None
            current_lines = []
        else:
            current_lines.append(line)
    flush()

    if not sections:
        sections.append(ParsedSection(order=0, page=None, section_title=None, text=text.strip()))
    return sections
