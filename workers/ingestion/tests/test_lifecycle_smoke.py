"""Behavioural smoke tests for the 5-state ingestion lifecycle.

Unlike ``test_ingestion_pipeline.py`` (which only walks the task sources
with ``ast`` to check that the expected SQL literals exist), these tests
actually execute each task body end-to-end against an in-memory SQLite DB
with all external services stubbed out.

Coverage:

* **Happy path** — a document goes
  ``uploaded → parsing → chunking → embedding → indexed``
  through the four tasks in sequence, with the ``send_task`` chain
  captured and replayed so every task runs its real Python body.

* **Failure path** — when ``parse_document`` raises, the document lands
  in ``state='failed'`` with the error message persisted, the chain is
  never started, and ``indexed`` is never reached.

SQLite in-memory is sufficient here because the worker tasks use only
portable SQL (``SELECT``/``INSERT``/``UPDATE`` with parametrised bind
values — no JSONB operators, no arrays, no RETURNING, no pgvector). See
``conftest.py`` for the detailed rationale.
"""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text

from app.services import parser as parser_module
from app.tasks.chunk_document import chunk_document_task
from app.tasks.embed_document import embed_document_task
from app.tasks.index_document import index_document_task
from app.tasks.parse_document import parse_document_task

TENANT_ID = "00000000-0000-0000-0000-000000000001"


def _seed_document(session_factory) -> str:
    """Insert a single ``uploaded`` document and return its id."""
    doc_id = str(uuid.uuid4())
    with session_factory() as db:
        db.execute(
            text(
                "INSERT INTO documents "
                "(id, tenant_id, name, mime_type, storage_key, state, "
                "tags, allowed_roles) "
                "VALUES (:id, :tenant, :name, :mime, :key, 'uploaded', "
                "'[]', '[\"member\"]')"
            ),
            {
                "id": doc_id,
                "tenant": TENANT_ID,
                "name": "smoke.txt",
                "mime": "text/plain",
                "key": "fake/storage/key",
            },
        )
        db.commit()
    return doc_id


def _get_state(session_factory, doc_id: str) -> str | None:
    with session_factory() as db:
        row = db.execute(
            text("SELECT state FROM documents WHERE id = :id"), {"id": doc_id}
        ).first()
    return None if row is None else row[0]


def _get_error(session_factory, doc_id: str) -> str | None:
    with session_factory() as db:
        row = db.execute(
            text("SELECT error FROM documents WHERE id = :id"), {"id": doc_id}
        ).first()
    return None if row is None else row[0]


def _count(session_factory, table: str, where_doc: str) -> int:
    with session_factory() as db:
        row = db.execute(
            text(f"SELECT COUNT(*) FROM {table} WHERE document_id = :id"),
            {"id": where_doc},
        ).first()
    return 0 if row is None else int(row[0])


def test_lifecycle_happy_path(lifecycle_env):
    """The 4 tasks, run in sequence with captured-and-replayed chaining,
    must walk the document from ``uploaded`` to ``indexed`` and never
    set a ``failed`` state along the way.
    """
    session_factory = lifecycle_env.session_factory
    captured = lifecycle_env.captured_send_task

    doc_id = _seed_document(session_factory)
    assert _get_state(session_factory, doc_id) == "uploaded"

    # --- parse ---------------------------------------------------------
    parse_document_task.apply(args=[doc_id]).get(propagate=True)
    assert _get_state(session_factory, doc_id) == "chunking"
    assert captured, "parse_document should have queued the chunk stage"
    name, args = captured[-1]
    assert name == "ingestion.chunk_document"

    # --- chunk ---------------------------------------------------------
    chunk_document_task.apply(args=args).get(propagate=True)
    assert _get_state(session_factory, doc_id) == "embedding"
    assert _count(session_factory, "document_chunks_parent", doc_id) >= 1
    assert _count(session_factory, "document_chunks_child", doc_id) >= 1
    name, args = captured[-1]
    assert name == "ingestion.embed_document"

    # --- embed ---------------------------------------------------------
    # By contract, embed_document must NOT touch the document state.
    embed_document_task.apply(args=args).get(propagate=True)
    assert _get_state(session_factory, doc_id) == "embedding"
    name, args = captured[-1]
    assert name == "ingestion.index_document"

    # --- index ---------------------------------------------------------
    index_document_task.apply(args=args).get(propagate=True)
    assert _get_state(session_factory, doc_id) == "indexed"
    assert _get_error(session_factory, doc_id) is None


def test_lifecycle_failure_path_sets_failed_state(
    lifecycle_env, monkeypatch: pytest.MonkeyPatch
):
    """If ``parse_document`` raises, the task must persist
    ``state='failed'`` with the error message, leave the chain empty, and
    never reach ``indexed``.
    """
    session_factory = lifecycle_env.session_factory
    captured = lifecycle_env.captured_send_task

    def _boom(content, mime_type, filename):  # noqa: ARG001
        raise RuntimeError("boom-from-smoke-test")

    monkeypatch.setattr(parser_module, "parse_document", _boom)

    # Also neutralise self.retry so .apply() fails fast with the original
    # exception instead of recursively re-running the task in eager mode.
    from celery.app.task import Task

    def _no_retry(self, exc=None, **kwargs):  # noqa: ARG001
        raise exc if exc is not None else RuntimeError("retry called in test")

    monkeypatch.setattr(Task, "retry", _no_retry)

    doc_id = _seed_document(session_factory)
    assert _get_state(session_factory, doc_id) == "uploaded"

    with pytest.raises(RuntimeError, match="boom-from-smoke-test"):
        parse_document_task.apply(args=[doc_id]).get(propagate=True)

    # State must have been flipped to 'failed' by the except: block in
    # parse_document_task, BEFORE the retry raised.
    assert _get_state(session_factory, doc_id) == "failed"
    error = _get_error(session_factory, doc_id) or ""
    assert "boom-from-smoke-test" in error

    # No further stages were queued, so the chain is empty.
    assert captured == []

    # And crucially, 'indexed' is unreachable.
    assert _get_state(session_factory, doc_id) != "indexed"
