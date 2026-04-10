"""Tests for rate limiting on /auth/login.

Static contract:
- login_limiter is imported and called in auth route
- 429 is returned after exceeding the limit

Live test drives the endpoint via dependency overrides.
"""
from __future__ import annotations

import pathlib

ROUTE_SRC = pathlib.Path(__file__).resolve().parent.parent / "app" / "api" / "routes" / "auth.py"


def _read() -> str:
    return ROUTE_SRC.read_text()


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
    def test_login_rate_limit_allows_normal_usage(self, client):
        """A single request should not trigger rate limiting."""
        r = client.post("/auth/login", json={"email": "a@b.com", "password": "x"})
        # 401 (bad creds) is fine \u2014 it means the rate limiter didn\u2019t block.
        assert r.status_code in (401, 422)

    def test_login_rate_limit_blocks_after_burst(self, client):
        """After 10+ rapid requests, 429 must appear."""
        for _ in range(12):
            r = client.post("/auth/login", json={"email": "a@b.com", "password": "x"})
        assert r.status_code == 429

