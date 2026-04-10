"""Tests for rate limiting on /auth/login.

Static contract:
- login_limiter is imported and called in auth route
- 429 is returned after exceeding the limit

Live test drives the endpoint with raise_server_exceptions=False so that
database errors (e.g. no PostgreSQL in CI-light envs) surface as 500
instead of raising, and we can still observe the 429 from the rate limiter.
"""
from __future__ import annotations

import pathlib

import pytest
from fastapi.testclient import TestClient

from app.core.rate_limit import login_limiter
from app.main import app

ROUTE_SRC = pathlib.Path(__file__).resolve().parent.parent / "app" / "api" / "routes" / "auth.py"


def _read() -> str:
    return ROUTE_SRC.read_text()


@pytest.fixture()
def _reset_limiter():
    """Clear the in-memory rate limiter between tests."""
    login_limiter._hits.clear()
    yield
    login_limiter._hits.clear()


class TestRateLimitStatic:
    def test_login_limiter_imported(self):
        src = _read()
        assert "login_limiter" in src

    def test_limiter_check_called(self):
        src = _read()
        assert "login_limiter.check(request)" in src

    def test_request_param_in_login(self):
        src = _read()
        assert "request: Request" in src


class TestRateLimitLive:
    def test_login_rate_limit_allows_normal_usage(self, _reset_limiter):
        """A single request should not trigger rate limiting."""
        with TestClient(app, raise_server_exceptions=False) as c:
            r = c.post("/auth/login", json={"email": "a@b.com", "password": "x"})
        # 401 (bad creds) or 500 (no DB) — either way, not 429.
        assert r.status_code != 429

    def test_login_rate_limit_blocks_after_burst(self, _reset_limiter):
        """After 10+ rapid requests, 429 must appear."""
        with TestClient(app, raise_server_exceptions=False) as c:
            for _ in range(12):
                r = c.post("/auth/login", json={"email": "a@b.com", "password": "x"})
        assert r.status_code == 429
