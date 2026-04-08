"""Tests for the 5-state document lifecycle contract."""

import ast
import pathlib


TASKS_DIR = pathlib.Path(__file__).resolve().parent.parent / "app" / "tasks"

VALID_STATES = {"uploaded", "parsing", "chunking", "embedding", "indexed", "failed"}


def _extract_state_literals(filepath: pathlib.Path) -> list[str]:
    """Extract state literals from SET state SQL."""
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
        assert "parsing" in states

    def test_sets_chunking_after_parse(self):
        states = _extract_state_literals(TASKS_DIR / "parse_document.py")
        assert "chunking" in states

    def test_does_not_set_indexed(self):
        states = _extract_state_literals(TASKS_DIR / "parse_document.py")
        assert "indexed" not in states

    def test_parsing_before_chunking(self):
        source = (TASKS_DIR / "parse_document.py").read_text()
        p = source.index("state = 'parsing'")
        c = source.index("state = 'chunking'")
        assert p < c


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
        assert "indexed" not in states


class TestIndexDocumentStates:
    def test_sets_indexed(self):
        states = _extract_state_literals(TASKS_DIR / "index_document.py")
        assert "indexed" in states

    def test_only_task_setting_indexed(self):
        for tf in TASKS_DIR.glob("*.py"):
            if tf.name == "__init__.py":
                continue
            states = _extract_state_literals(tf)
            if tf.name == "index_document.py":
                assert "indexed" in states
            else:
                assert "indexed" not in states


class TestAllStatesValid:
    def test_no_unknown_states(self):
        for tf in TASKS_DIR.glob("*.py"):
            if tf.name == "__init__.py":
                continue
            for s in _extract_state_literals(tf):
                assert s in VALID_STATES
