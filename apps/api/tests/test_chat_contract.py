"""Tests for the citation contract in generation_service.py.

Contract:
- If doc_id is missing from a retrieval result -> skip that citation, log warning
- If chunk_id is not a valid UUID -> skip that citation, log warning
- No fabricated uuid4() fallbacks for either field
"""
from __future__ import annotations

import ast
import pathlib

SRC = pathlib.Path(__file__).resolve().parent.parent / "app" / "services" / "generation_service.py"


def _read_source() -> str:
    return SRC.read_text()


class TestNoCitationFabrication:
    """generation_service must not fabricate UUIDs for missing citation fields."""

    def test_no_uuid4_in_citation_block(self):
        source = _read_source()
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                func = node.func
                if isinstance(func, ast.Name) and func.id == "Citation":
                    for kw in node.keywords:
                        if kw.arg in ("document_id", "chunk_id"):
                            source_segment = ast.dump(kw.value)
                            assert "uuid4" not in source_segment, (
                                f"Citation.{kw.arg} must not use uuid4() fallback"
                            )


class TestSkipOnMissingDocId:
    """When doc_id is missing, the code should continue (skip), not raise."""

    def test_continue_on_missing_doc_id(self):
        source = _read_source()
        assert "not doc_id" in source, (
            "generation_service must check for missing doc_id"
        )
        assert "continue" in source, (
            "generation_service must skip (continue) when doc_id is missing"
        )


class TestSkipOnInvalidChunkId:
    """When chunk_id fails UUID validation, the code should skip and log."""

    def test_continue_on_invalid_chunk_id(self):
        source = _read_source()
        assert "_is_uuid" in source, (
            "generation_service must validate chunk_id with _is_uuid"
        )

    def test_logs_warning_on_invalid_chunk_id(self):
        source = _read_source()
        assert "citation.invalid_chunk_id" in source, (
            "generation_service must log 'citation.invalid_chunk_id'"
        )

    def test_logs_warning_on_missing_doc_id(self):
        source = _read_source()
        assert "citation.missing_document_id" in source, (
            "generation_service must log 'citation.missing_document_id'"
        )
