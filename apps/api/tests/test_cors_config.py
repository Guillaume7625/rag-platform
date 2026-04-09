"""Tests for A1 CORS hardening.

Static contract:
- settings.cors_origins is a list[str]
- "*" is NOT in the default (no wildcard).
- main.py wires CORSMiddleware with settings.cors_origins.

Live smoke (deterministic, infra-free):
- Preflight with an allowed origin reflects the origin in ACAO.
- Preflight with a disallowed origin does not reflect it.
- Simple GET /health with an allowed origin reflects ACAO.
"""
from __future__ import annotations

import pathlib

from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app

MAIN_SRC = pathlib.Path(__file__).resolve().parent.parent / "app" / "main.py"


def _read_main() -> str:
    return MAIN_SRC.read_text()


class TestCorsConfigStatic:
    def test_cors_origins_is_list(self):
        assert isinstance(settings.cors_origins, list)

    def test_cors_origins_not_wildcard(self):
        assert "*" not in settings.cors_origins

    def test_cors_origins_has_default(self):
        assert len(settings.cors_origins) >= 1

    def test_main_uses_settings_cors_origins(self):
        src = _read_main()
        assert "allow_origins=settings.cors_origins" in src
        assert 'allow_origins=["*"]' not in src


class TestCorsLiveSmoke:
    """Live preflight / simple-request behavior via CORSMiddleware."""

    def setup_method(self):
        self.client = TestClient(app)
        self.allowed = settings.cors_origins[0]

    def test_preflight_allowed_origin_is_reflected(self):
        r = self.client.options(
            "/health",
            headers={
                "Origin": self.allowed,
                "Access-Control-Request-Method": "GET",
            },
        )
        assert r.status_code == 200
        assert r.headers.get("access-control-allow-origin") == self.allowed

    def test_preflight_disallowed_origin_is_not_reflected(self):
        r = self.client.options(
            "/health",
            headers={
                "Origin": "http://evil.example",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert r.headers.get("access-control-allow-origin") != "http://evil.example"

    def test_simple_get_with_allowed_origin_reflects(self):
        r = self.client.get("/health", headers={"Origin": self.allowed})
        assert r.status_code == 200
        assert r.headers.get("access-control-allow-origin") == self.allowed
