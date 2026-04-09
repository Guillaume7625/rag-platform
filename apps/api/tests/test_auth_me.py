"""Tests for A2 auth /me endpoints.

Static contract:
- UserUpdate exists with full_name field
- Schema source contains min_length=1, max_length=255 on full_name
- CurrentUser dataclass carries full_name
- routes/auth.py declares @router.patch("/me")
- GET /me no longer hardcodes full_name=None

Live functional tests use dependency_overrides to drive the handlers without
a real database.
"""
from __future__ import annotations

import pathlib

from app.schemas.auth import UserUpdate

ROUTE_SRC = (
    pathlib.Path(__file__).resolve().parent.parent / "app" / "api" / "routes" / "auth.py"
)
SCHEMA_SRC = (
    pathlib.Path(__file__).resolve().parent.parent / "app" / "schemas" / "auth.py"
)
DEPS_SRC = (
    pathlib.Path(__file__).resolve().parent.parent / "app" / "api" / "deps.py"
)


def _read(p: pathlib.Path) -> str:
    return p.read_text()


class TestAuthMeStatic:
    def test_user_update_schema_exposes_full_name(self):
        assert "full_name" in UserUpdate.model_fields

    def test_user_update_constraints_present_in_source(self):
        src = _read(SCHEMA_SRC)
        assert "full_name: str = Field" in src
        assert "min_length=1" in src
        assert "max_length=255" in src

    def test_currentuser_has_full_name(self):
        src = _read(DEPS_SRC)
        assert "full_name: str | None" in src

    def test_patch_me_route_declared(self):
        src = _read(ROUTE_SRC)
        assert '@router.patch("/me"' in src

    def test_get_me_returns_current_full_name(self):
        src = _read(ROUTE_SRC)
        assert "full_name=current.full_name" in src
        assert "full_name=None" not in src


class _FakeUserRow:
    """Mutable stand-in for a SQLAlchemy User row."""

    def __init__(self, id, email, full_name):
        self.id = id
        self.email = email
        self.full_name = full_name


class TestAuthMeLive:
    def test_get_me_returns_profile(self, client_auth):
        client, user, _ = client_auth
        r = client.get("/auth/me")
        assert r.status_code == 200
        body = r.json()
        assert body["email"] == user.email
        assert body["full_name"] == user.full_name
        assert body["tenant_id"] == str(user.tenant_id)
        assert body["role"] == user.role

    def test_patch_me_happy_path(self, client_auth):
        client, user, db = client_auth
        row = _FakeUserRow(id=user.id, email=user.email, full_name="Old Name")
        db.query.return_value.filter.return_value.first.return_value = row

        r = client.patch("/auth/me", json={"full_name": "New Name"})
        assert r.status_code == 200
        body = r.json()
        assert body["full_name"] == "New Name"
        assert row.full_name == "New Name"
        assert db.commit.called
        assert db.refresh.called

    def test_patch_me_user_not_found(self, client_auth):
        client, _, db = client_auth
        db.query.return_value.filter.return_value.first.return_value = None
        r = client.patch("/auth/me", json={"full_name": "Whatever"})
        assert r.status_code == 404

    def test_patch_me_empty_body_422(self, client_auth):
        client, *_ = client_auth
        r = client.patch("/auth/me", json={})
        assert r.status_code == 422

    def test_patch_me_empty_name_422(self, client_auth):
        client, *_ = client_auth
        r = client.patch("/auth/me", json={"full_name": ""})
        assert r.status_code == 422

    def test_patch_me_oversize_name_422(self, client_auth):
        client, *_ = client_auth
        r = client.patch("/auth/me", json={"full_name": "x" * 256})
        assert r.status_code == 422
