"""Tests for the 5-state document lifecycle contract.

Spec lifecycle: uploaded -> parsing -> chunking -> embedding -> indexed
Each task file must only set specific states:
- parse_document: sets 'parsing' then 'chunking'
- chunk_document: sets 'embedding'
- embed_document: does NOT set 'indexed'
- index_document: sets 'indexed' (terminal)
- any task on error: sets 'failed'
"""
from __future__ import annotations

import ast
import pathlib


TASKS_DIR = pathlib.Path(__file__).resolve().parent.parent / "app" / "tasks"

VALID_STATES = {"uploaded", "parsing", "chunking", "embedding", "indexed", "failed"}


def _extract_state_literals(filepath: pathlib.Path) -> list[str]:
    """Extract all string literals used in SET state = '...' SQL from a task file."""
    source = filepath.read_text()
    states: list[str] = []
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            val = node.value
            if "SET state = '" in val:
                start = val.index("SET state = '") + len("SET state = '")
                end = val.index("'", start)
                states.append(val[start:end])
    return states


class TestParseDocumentStates:
    def test_sets_parsing_before_work(self):
        states = _extract_state_literals(TASKS_DIR / "parse_document.py")
        assert "parsing" in states, "parse_document must set state='parsing'"

    def test_sets_chunking_after_parse(self):
        states = _extract_state_literals(TASKS_DIR / "parse_document.py")
        assert "chunking" in states, "parse_document must set state='chunking'"

    def test_sets_failed_on_error(self):
        states = _extract_state_literals(TASKS_DIR / "parse_document.py")
        assert "failed" in states

    def test_does_not_set_indexed(self):
        states = _extract_state_literals(TASKS_DIR / "parse_document.py")
        assert "indexed" not in states, "parse_document must NOT set 'indexed'"

    def test_parsing_appears_before_chunking(self):
        source = (TASKS_DIR / "parse_document.py").read_text()
        parsing_pos = source.index("state = 'parsing'")
        chunking_pos = source.index("state = 'chunking'")
        assert parsing_pos < chunking_pos, "parsing must be set before chunking"


class TestChunkDocumentStates:
    def test_sets_embedding(self):
        states = _extract_state_literals(TASKS_DIR / "chunk_document.py")
        assert "embedding" in states

    def test_does_not_set_indexed(self):
        states = _extract_state_literals(TASKS_DIR / "chunk_document.py")
        assert "indexed" not in states


class TestEmbedDocumentStates:
    def test_does_not_set_indexed(self):
        states = _extract_state_literals(TASKS_DIR / "embed_document.py")
        assert "indexed" not in states, "embed_document must NOT set 'indexed'"

    def test_sets_failed_on_error(self):
        states = _extract_state_literals(TASKS_DIR / "embed_document.py")
        assert "failed" in states


class TestIndexDocumentStates:
    def test_sets_indexed(self):
        states = _extract_state_literals(TASKS_DIR / "index_document.py")
        assert "indexed" in states, "index_document must set 'indexed'"

    def test_is_only_task_setting_indexed(self):
        for task_file in TASKS_DIR.glob("*.py"):
            if task_file.name == "__init__.py":
                continue
            states = _extract_state_literals(task_file)
            if task_file.name == "index_document.py":
                assert "indexed" in states
            else:
                assert "indexed" not in states, (
                    f"{task_file.name} must not set 'indexed'"
                )


class TestAllStatesValid:
    def test_no_unknown_states(self):
        for task_file in TASKS_DIR.glob("*.py"):
            if task_file.name == "__init__.py":
                continue
            states = _extract_state_literals(task_file)
            for s in states:
                assert s in VALID_STATES, (
                    f"{task_file.name} uses unknown state '{s}'"
                )
