"""Tests for A3 GET /documents filters + pagination.

Static contract:
- Query is imported from fastapi in the documents route
- list_documents signature has state / tags / limit / offset
- Filter logic uses Document.state == and Document.tags.contains
- DocumentListResponse envelope exposes limit / offset / has_more

Live functional tests drive the handler via dependency_overrides with a
MagicMock session whose query chain is configured per test.
"""
from __future__ import annotations

import pathlib
import uuid
from datetime import UTC, datetime

from app.schemas.document import DocumentListResponse

ROUTE_SRC = (
    pathlib.Path(__file__).resolve().parent.parent / "app" / "api" / "routes" / "documents.py"
)


def _read() -> str:
    return ROUTE_SRC.read_text()


class TestDocumentsFiltersStatic:
    def test_query_imported(self):
        src = _read()
        assert "from fastapi import" in src
        assert "Query" in src

    def test_list_documents_has_state_param(self):
        src = _read()
        assert "state: str | None = Query" in src

    def test_list_documents_has_tags_param(self):
        src = _read()
        assert "tags: list[str] | None = Query" in src

    def test_list_documents_has_limit_offset_bounds(self):
        src = _read()
        assert "limit: int = Query(default=50, ge=1, le=200)" in src
        assert "offset: int = Query(default=0, ge=0)" in src

    def test_list_documents_filters_on_state(self):
        src = _read()
        assert "Document.state == state" in src

    def test_list_documents_filters_on_tags_contains(self):
        src = _read()
        assert "Document.tags.contains(tags)" in src

    def test_envelope_fields_declared(self):
        fields = DocumentListResponse.model_fields
        assert "items" in fields
        assert "total" in fields
        assert "limit" in fields
        assert "offset" in fields
        assert "has_more" in fields


class _FakeDoc:
    def __init__(self, tenant_id, name="test.pdf", state="indexed"):
        self.id = uuid.uuid4()
        self.tenant_id = tenant_id
        self.name = name
        self.mime_type = "application/pdf"
        self.size_bytes = 1024
        self.state = state
        self.tags = ["finance"]
        self.allowed_roles = ["member"]
        self.created_at = datetime.now(UTC)
        self.updated_at = datetime.now(UTC)
        self.error = None


def _configure_chain(db, rows, total):
    q = db.query.return_value
    q.filter.return_value = q
    q.order_by.return_value = q
    q.offset.return_value = q
    q.limit.return_value = q
    q.count.return_value = total
    q.all.return_value = rows


class TestDocumentsFiltersLive:
    def test_list_documents_happy_path(self, client_auth):
        client, user, db = client_auth
        rows = [_FakeDoc(tenant_id=user.tenant_id)]
        _configure_chain(db, rows, total=1)

        r = client.get("/documents?limit=20&offset=0")
        assert r.status_code == 200
        body = r.json()
        assert body["total"] == 1
        assert body["limit"] == 20
        assert body["offset"] == 0
        assert body["has_more"] is False
        assert len(body["items"]) == 1

    def test_list_documents_has_more_true(self, client_auth):
        client, user, db = client_auth
        rows = [_FakeDoc(tenant_id=user.tenant_id)]
        _configure_chain(db, rows, total=57)

        r = client.get("/documents?limit=20&offset=10")
        assert r.status_code == 200
        body = r.json()
        assert body["total"] == 57
        assert body["limit"] == 20
        assert body["offset"] == 10
        assert body["has_more"] is True

    def test_list_documents_empty_result(self, client_auth):
        client, _, db = client_auth
        _configure_chain(db, rows=[], total=0)
        r = client.get("/documents")
        body = r.json()
        assert body["items"] == []
        assert body["total"] == 0
        assert body["has_more"] is False
        # Defaults echoed back
        assert body["limit"] == 50
        assert body["offset"] == 0

    def test_list_documents_with_filters_accepted(self, client_auth):
        client, _, db = client_auth
        _configure_chain(db, rows=[], total=0)
        r = client.get(
            "/documents?state=indexed&tags=finance&tags=q1&limit=5&offset=0"
        )
        assert r.status_code == 200

    def test_list_documents_limit_out_of_range(self, client_auth):
        client, *_ = client_auth
        r = client.get("/documents?limit=1000")
        assert r.status_code == 422

    def test_list_documents_offset_negative(self, client_auth):
        client, *_ = client_auth
        r = client.get("/documents?offset=-1")
        assert r.status_code == 422

    def test_list_documents_without_token_is_401(self, client):
        r = client.get("/documents")
        assert r.status_code == 401
