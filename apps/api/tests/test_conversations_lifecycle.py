"""Tests for A4 PATCH/DELETE /conversations/{conv_id}.

Static contract:
- ConversationUpdate schema exists and has a `title` field
- routes/conversations.py declares PATCH and DELETE on /{conv_id}
- DELETE handler uses HTTP_204_NO_CONTENT
- Existing GET handlers are untouched (by presence)

Live functional tests drive the handlers via dependency_overrides.
"""
from __future__ import annotations

import pathlib
import uuid
from datetime import UTC, datetime

from app.schemas.conversation import ConversationUpdate

ROUTE_SRC = (
    pathlib.Path(__file__).resolve().parent.parent
    / "app"
    / "api"
    / "routes"
    / "conversations.py"
)
SCHEMA_SRC = (
    pathlib.Path(__file__).resolve().parent.parent
    / "app"
    / "schemas"
    / "conversation.py"
)


def _read(p: pathlib.Path) -> str:
    return p.read_text()


class TestConversationsLifecycleStatic:
    def test_conversation_update_schema_has_title(self):
        assert "title" in ConversationUpdate.model_fields

    def test_conversation_update_constraints_in_source(self):
        src = _read(SCHEMA_SRC)
        assert "title: str = Field" in src
        assert "min_length=1" in src
        assert "max_length=512" in src

    def test_patch_route_declared(self):
        src = _read(ROUTE_SRC)
        assert '@router.patch("/{conv_id}"' in src

    def test_delete_route_declared(self):
        src = _read(ROUTE_SRC)
        assert '@router.delete("/{conv_id}"' in src

    def test_delete_uses_204(self):
        src = _read(ROUTE_SRC)
        assert "HTTP_204_NO_CONTENT" in src

    def test_get_handlers_still_present(self):
        src = _read(ROUTE_SRC)
        assert "def list_conversations" in src
        assert "def get_conversation" in src


class _FakeConv:
    def __init__(self, tenant_id, user_id, title="Old title"):
        self.id = uuid.uuid4()
        self.tenant_id = tenant_id
        self.user_id = user_id
        self.title = title
        self.created_at = datetime.now(UTC)


def _stub_first(db, conv):
    db.query.return_value.filter.return_value.first.return_value = conv


class TestConversationsLifecycleLive:
    def test_patch_happy_path(self, client_auth):
        client, user, db = client_auth
        conv = _FakeConv(tenant_id=user.tenant_id, user_id=user.id)
        _stub_first(db, conv)

        r = client.patch(f"/conversations/{conv.id}", json={"title": "New title"})
        assert r.status_code == 200
        body = r.json()
        assert body["title"] == "New title"
        assert conv.title == "New title"
        assert db.commit.called
        assert db.refresh.called

    def test_patch_not_found(self, client_auth):
        client, _, db = client_auth
        _stub_first(db, None)
        r = client.patch(
            f"/conversations/{uuid.uuid4()}", json={"title": "ignored"}
        )
        assert r.status_code == 404

    def test_patch_missing_title_422(self, client_auth):
        client, *_ = client_auth
        r = client.patch(f"/conversations/{uuid.uuid4()}", json={})
        assert r.status_code == 422

    def test_patch_empty_title_422(self, client_auth):
        client, *_ = client_auth
        r = client.patch(f"/conversations/{uuid.uuid4()}", json={"title": ""})
        assert r.status_code == 422

    def test_patch_oversize_title_422(self, client_auth):
        client, *_ = client_auth
        r = client.patch(
            f"/conversations/{uuid.uuid4()}", json={"title": "x" * 513}
        )
        assert r.status_code == 422

    def test_delete_happy_path(self, client_auth):
        client, user, db = client_auth
        conv = _FakeConv(tenant_id=user.tenant_id, user_id=user.id)
        _stub_first(db, conv)

        r = client.delete(f"/conversations/{conv.id}")
        assert r.status_code == 204
        assert r.text == ""
        assert db.delete.called
        assert db.commit.called

    def test_delete_not_found(self, client_auth):
        client, _, db = client_auth
        _stub_first(db, None)
        r = client.delete(f"/conversations/{uuid.uuid4()}")
        assert r.status_code == 404
