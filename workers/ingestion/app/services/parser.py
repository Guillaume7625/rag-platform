"""Document parser.

Primary: Docling for structured parsing (PDF, DOCX, PPTX, HTML, MD).
Fallback: plain UTF-8 decode for text-like formats.
OCR fallback for scanned PDFs is left as a TODO hook.
"""
from __future__ import annotations

import io
import logging
import tempfile
from dataclasses import dataclass
from pathlib import Path

log = logging.getLogger(__name__)


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

            # Primary: use DocumentStream if available
            try:
                from docling.datamodel.base_models import DocumentStream  # type: ignore

                source = DocumentStream(name=filename, stream=io.BytesIO(content))
                result = converter.convert(source)
            except ImportError:
                # Fallback: write to tempfile and pass the path
                suffix = Path(filename).suffix or ".bin"
                with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
                    tmp.write(content)
                    tmp.flush()
                    tmp_path = tmp.name
                try:
                    result = converter.convert(source=tmp_path)
                finally:
                    Path(tmp_path).unlink(missing_ok=True)

            md = result.document.export_to_markdown()
            return _split_markdown(md)
        except Exception as exc:
            log.warning("docling_parse_failed: %s – falling back to plain-text", exc)
            if mime_type == "application/pdf":
                raise RuntimeError(f"PDF parsing failed: {exc}") from exc

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
    text = text.replace("\x00", "")
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
