import uuid
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser, get_current_user
from app.db.session import get_db
from app.main import app


@pytest.fixture()
def client() -> TestClient:
    """Raw TestClient with no dependency overrides.

    Used by tests that hit unauthenticated endpoints (e.g. /health) or that
    need to observe the real 401 behavior of protected routes.
    """
    return TestClient(app)


@pytest.fixture()
def fake_user() -> CurrentUser:
    """Deterministic CurrentUser for dependency-override based tests."""
    return CurrentUser(
        id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
        email="test@example.com",
        tenant_id=uuid.UUID("00000000-0000-0000-0000-000000000002"),
        role="member",
        full_name="Test User",
    )


@pytest.fixture()
def mock_db() -> MagicMock:
    """A MagicMock session that tests configure per-case.

    Handlers call chains like db.query(Model).filter(...).all() — each link
    returns another MagicMock by default, which tests override to inject
    fake rows and assert on .commit / .delete / .refresh side effects.
    """
    return MagicMock(spec=Session)


@pytest.fixture()
def client_auth(fake_user: CurrentUser, mock_db: MagicMock):
    """TestClient with get_current_user and get_db overridden.

    Yields a tuple (client, fake_user, mock_db). Overrides are cleared on
    teardown so they never leak into unrelated tests.
    """

    def _override_user() -> CurrentUser:
        return fake_user

    def _override_db():
        yield mock_db

    app.dependency_overrides[get_current_user] = _override_user
    app.dependency_overrides[get_db] = _override_db
    try:
        yield TestClient(app), fake_user, mock_db
    finally:
        app.dependency_overrides.clear()
