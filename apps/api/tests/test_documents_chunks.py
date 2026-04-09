"""Tests for A5 GET /documents/{doc_id}/chunks.

Static contract:
- Handler registered at GET /{doc_id}/chunks
- Queries DocumentChunkParent (parent chunks only)
- Ordered by order_index
- CHUNK_CONTENT_PREVIEW_CHARS constant is 500
- Tenant ownership enforced via _must_get BEFORE any chunk query

Live functional tests drive the handler via dependency_overrides. The handler
calls db.query() twice with different models (Document, then
DocumentChunkParent); we branch via side_effect.
"""
from __future__ import annotations

import pathlib
import uuid
from unittest.mock import MagicMock

from app.db.models.chunk import DocumentChunkParent
from app.db.models.document import Document
from app.schemas.document import DocumentChunkOut, DocumentChunksResponse

ROUTE_SRC = (
    pathlib.Path(__file__).resolve().parent.parent / "app" / "api" / "routes" / "documents.py"
)


def _read() -> str:
    return ROUTE_SRC.read_text()


class TestDocumentsChunksStatic:
    def test_chunks_route_declared(self):
        src = _read()
        assert '@router.get("/{doc_id}/chunks"' in src

    def test_chunks_queries_parent_table(self):
        src = _read()
        assert "DocumentChunkParent" in src
        assert "order_index" in src

    def test_chunks_preview_constant_is_500(self):
        src = _read()
        assert "CHUNK_CONTENT_PREVIEW_CHARS = 500" in src

    def test_chunks_tenant_enforced_via_must_get(self):
        src = _read()
        assert "_must_get(db, doc_id, current.tenant_id)" in src

    def test_schemas_exported(self):
        assert "items" in DocumentChunksResponse.model_fields
        assert "document_id" in DocumentChunksResponse.model_fields
        assert "has_more" in DocumentChunksResponse.model_fields
        assert "truncated" in DocumentChunkOut.model_fields
        assert "content" in DocumentChunkOut.model_fields


class _FakeDoc:
    def __init__(self, tenant_id):
        self.id = uuid.uuid4()
        self.tenant_id = tenant_id
        self.name = "doc.pdf"
        self.state = "indexed"


class _FakeChunk:
    def __init__(self, order_index, content, page=1, section="Section"):
        self.id = uuid.uuid4()
        self.order_index = order_index
        self.page = page
        self.section_title = section
        self.content = content
        self.token_count = 100


def _wire_branching_query(db, *, doc_row, chunks, total):
    """Route db.query(Document) and db.query(DocumentChunkParent) to
    distinct mock chains.
    """

    def side_effect(model):
        if model is Document:
            doc_q = MagicMock()
            doc_q.filter.return_value.first.return_value = doc_row
            return doc_q
        if model is DocumentChunkParent:
            chunk_q = MagicMock()
            chunk_q.filter.return_value = chunk_q
            chunk_q.order_by.return_value = chunk_q
            chunk_q.offset.return_value = chunk_q
            chunk_q.limit.return_value = chunk_q
            chunk_q.count.return_value = total
            chunk_q.all.return_value = chunks
            return chunk_q
        raise AssertionError(f"unexpected query target: {model}")

    db.query.side_effect = side_effect


class TestDocumentsChunksLive:
    def test_chunks_happy_path_with_truncation(self, client_auth):
        client, user, db = client_auth
        doc = _FakeDoc(tenant_id=user.tenant_id)
        long_content = "x" * 800
        short_content = "y" * 200
        chunks = [
            _FakeChunk(order_index=0, content=long_content),
            _FakeChunk(order_index=1, content=short_content),
        ]
        _wire_branching_query(db, doc_row=doc, chunks=chunks, total=2)

        r = client.get(f"/documents/{doc.id}/chunks")
        assert r.status_code == 200
        body = r.json()
        assert body["document_id"] == str(doc.id)
        assert body["total"] == 2
        assert body["has_more"] is False
        assert len(body["items"]) == 2

        first, second = body["items"]
        assert first["truncated"] is True
        assert len(first["content"]) == 500
        assert second["truncated"] is False
        assert len(second["content"]) == 200
        assert second["content"] == "y" * 200

    def test_chunks_document_not_found(self, client_auth):
        client, user, db = client_auth
        _wire_branching_query(db, doc_row=None, chunks=[], total=0)
        r = client.get(f"/documents/{uuid.uuid4()}/chunks")
        assert r.status_code == 404

    def test_chunks_empty_document(self, client_auth):
        client, user, db = client_auth
        doc = _FakeDoc(tenant_id=user.tenant_id)
        _wire_branching_query(db, doc_row=doc, chunks=[], total=0)
        r = client.get(f"/documents/{doc.id}/chunks")
        assert r.status_code == 200
        body = r.json()
        assert body["items"] == []
        assert body["total"] == 0
        assert body["has_more"] is False

    def test_chunks_default_pagination(self, client_auth):
        client, user, db = client_auth
        doc = _FakeDoc(tenant_id=user.tenant_id)
        _wire_branching_query(db, doc_row=doc, chunks=[], total=0)
        r = client.get(f"/documents/{doc.id}/chunks")
        body = r.json()
        assert body["limit"] == 100
        assert body["offset"] == 0

    def test_chunks_limit_out_of_range(self, client_auth):
        client, *_ = client_auth
        r = client.get(f"/documents/{uuid.uuid4()}/chunks?limit=1000")
        assert r.status_code == 422

    def test_chunks_offset_negative(self, client_auth):
        client, *_ = client_auth
        r = client.get(f"/documents/{uuid.uuid4()}/chunks?offset=-1")
        assert r.status_code == 422
