"""Shared pytest fixtures for the ingestion worker tests.

The lifecycle smoke tests (``test_lifecycle_smoke.py``) need a minimal
Postgres-like DB, all external I/O neutralised, and a way to drive the
Celery task chain without a broker.

Design notes:
- SQLite in-memory + ``StaticPool`` so every ``SessionLocal()`` call sees
  the same database (default SQLite pools would give each connection its
  own fresh in-memory DB, breaking the multi-session task flow).
- We patch ``app.db.engine`` / ``app.db.SessionLocal`` rather than swap the
  ``DATABASE_URL`` at import time; this keeps the production ``app.db``
  module untouched.
- ``celery_app.send_task`` is monkeypatched to capture ``(name, args)``
  tuples instead of routing through a broker. The smoke test then replays
  the captured calls explicitly, which exercises every task's real body
  while keeping the test deterministic.
- The embedder is used as-is: its built-in fallback mode kicks in when
  ``voyage_api_key`` is empty (the default in tests), so no network is
  reached.
"""
from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# NOTE: importing app.db here is safe — SQLAlchemy is lazy and will not
# attempt to connect to Postgres until a query is issued.
from app import db as app_db
from app.services import parser as parser_module
from app.tasks import index_document as index_task_module
from app.tasks import parse_document as parse_task_module
from app.worker import celery_app

# Minimal subset of the Postgres schema, translated to SQLite-compatible DDL.
# Only the columns actually read or written by the 4 lifecycle tasks are
# present. JSONB columns become TEXT (we never inspect their structure in
# these tests — Qdrant is mocked).
_DDL_STATEMENTS: tuple[str, ...] = (
    """
    CREATE TABLE documents (
        id TEXT PRIMARY KEY,
        tenant_id TEXT NOT NULL,
        name TEXT NOT NULL,
        mime_type TEXT,
        storage_key TEXT NOT NULL,
        state TEXT NOT NULL DEFAULT 'uploaded',
        error TEXT,
        tags TEXT DEFAULT '[]',
        allowed_roles TEXT DEFAULT '["member"]'
    )
    """,
    """
    CREATE TABLE document_versions (
        id TEXT PRIMARY KEY,
        document_id TEXT NOT NULL,
        version INTEGER NOT NULL
    )
    """,
    """
    CREATE TABLE document_chunks_parent (
        id TEXT PRIMARY KEY,
        document_id TEXT NOT NULL,
        document_version_id TEXT,
        order_index INTEGER NOT NULL,
        page INTEGER,
        section_title TEXT,
        content TEXT NOT NULL,
        token_count INTEGER
    )
    """,
    """
    CREATE TABLE document_chunks_child (
        id TEXT PRIMARY KEY,
        parent_id TEXT NOT NULL,
        document_id TEXT NOT NULL,
        order_index INTEGER NOT NULL,
        content TEXT NOT NULL,
        token_count INTEGER
    )
    """,
)


@dataclass
class LifecycleEnv:
    """Handles returned to the smoke tests."""

    engine: Any
    session_factory: Any
    captured_send_task: list[tuple[str, list[Any]]]


def _build_test_engine() -> Any:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    with engine.begin() as conn:
        for ddl in _DDL_STATEMENTS:
            conn.execute(text(ddl))
    return engine


@pytest.fixture
def lifecycle_env(monkeypatch: pytest.MonkeyPatch) -> Iterator[LifecycleEnv]:
    """Stand up an isolated lifecycle environment.

    Patches applied (all torn down by pytest at the end of the test):

    * ``app.db.engine`` / ``app.db.SessionLocal`` → SQLite in-memory
    * ``app.services.storage.get_object_bytes`` → fake bytes
    * ``app.services.parser.parse_document``    → single fixed section
    * ``app.services.indexer.get_client``       → inert stub
    * ``app.services.indexer.ensure_collection``→ no-op
    * ``app.services.indexer.upsert_points``    → no-op
    * ``celery_app.send_task``                  → capture into a list
    """
    engine = _build_test_engine()
    session_factory = sessionmaker(
        bind=engine, autoflush=False, autocommit=False, future=True
    )

    # Redirect the worker's DB module at the SessionLocal name so that
    # ``session_scope()`` (which does ``db = SessionLocal()`` at call time)
    # picks up the test factory without needing to patch session_scope itself.
    monkeypatch.setattr(app_db, "engine", engine)
    monkeypatch.setattr(app_db, "SessionLocal", session_factory)

    # IMPORTANT: the task modules use ``from app.services.X import Y``,
    # which captures ``Y`` as a local name at import time. Patching the
    # service module alone has no effect — we must patch the name in
    # each task module namespace where it is actually resolved.

    # Neutralise MinIO inside parse_document_task.
    monkeypatch.setattr(
        parse_task_module, "get_object_bytes", lambda key: b"irrelevant-test-bytes"
    )

    # Deterministic parser output: one section with a short text.
    def _fake_parse(content: bytes, mime_type: str, filename: str):  # noqa: ARG001
        return [
            parser_module.ParsedSection(
                order=0,
                page=1,
                section_title="Smoke Section",
                text="hello world this is a tiny document used by the smoke test",
            )
        ]

    monkeypatch.setattr(parse_task_module, "parse_document", _fake_parse)

    # Neutralise Qdrant inside index_document_task. ``get_client`` must
    # return *something* because ``ensure_collection`` /
    # ``upsert_points`` take it as a parameter.
    monkeypatch.setattr(index_task_module, "get_client", lambda: object())
    monkeypatch.setattr(index_task_module, "ensure_collection", lambda client: None)
    monkeypatch.setattr(
        index_task_module, "upsert_points", lambda client, points: None
    )

    # Capture (not dispatch) Celery task chaining. The smoke test replays
    # the captured calls explicitly so the real task bodies keep running.
    captured: list[tuple[str, list[Any]]] = []

    def _capture_send_task(name: str, args: Any = None, **_kwargs: Any) -> None:
        captured.append((name, list(args or [])))

    monkeypatch.setattr(celery_app, "send_task", _capture_send_task)

    yield LifecycleEnv(
        engine=engine,
        session_factory=session_factory,
        captured_send_task=captured,
    )

    engine.dispose()
