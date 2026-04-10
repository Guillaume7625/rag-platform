"""Tests for security headers middleware.

Verifies that every response includes the protective headers added by
SecurityHeadersMiddleware.  Uses GET /health as the probe endpoint.
"""
from fastapi.testclient import TestClient


class TestSecurityHeaders:
    def test_x_content_type_options(self, client: TestClient) -> None:
        r = client.get("/health")
        assert r.headers.get("X-Content-Type-Options") == "nosniff"

    def test_x_frame_options(self, client: TestClient) -> None:
        r = client.get("/health")
        assert r.headers.get("X-Frame-Options") == "DENY"

    def test_referrer_policy(self, client: TestClient) -> None:
        r = client.get("/health")
        assert r.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"

    def test_permissions_policy(self, client: TestClient) -> None:
        r = client.get("/health")
        assert r.headers.get("Permissions-Policy") == "camera=(), microphone=(), geolocation=()"
