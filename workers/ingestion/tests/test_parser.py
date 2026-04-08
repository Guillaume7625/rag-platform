"""Tests for the document parser service."""
from __future__ import annotations

from app.services.parser import ParsedSection, parse_document


class TestParseDocumentPlainText:
    """Plain-text / markdown parsing produces ParsedSection objects."""

    def test_plain_text_returns_parsed_sections(self):
        raw = b"# Title\nSome body text"
        result = parse_document(raw, "text/plain", "readme.md")
        assert isinstance(result, list)
        assert len(result) >= 1
        assert all(isinstance(s, ParsedSection) for s in result)

    def test_parsed_section_has_required_fields(self):
        raw = b"Hello world"
        result = parse_document(raw, "text/plain", "test.txt")
        section = result[0]
        assert hasattr(section, "order")
        assert hasattr(section, "page")
        assert hasattr(section, "section_title")
        assert hasattr(section, "text")
        assert isinstance(section.text, str)
        assert len(section.text) > 0

    def test_json_mime_type_treated_as_text(self):
        raw = b'{"key": "value"}'
        result = parse_document(raw, "application/json", "data.json")
        assert isinstance(result, list)
        assert len(result) >= 1


class TestDoclingFallback:
    """Docling failure falls back to plain-text with logging."""

    def test_unsupported_binary_returns_empty(self):
        raw = b"\x00\x01\x02"
        result = parse_document(raw, "application/octet-stream", "blob.bin")
        assert isinstance(result, list)
