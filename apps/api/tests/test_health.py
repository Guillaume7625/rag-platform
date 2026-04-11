"""Tests for health endpoints."""
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app, raise_server_exceptions=False)


def test_health() -> None:
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_readiness_returns_checks() -> None:
    r = client.get("/health/ready")
    assert r.status_code == 200
    data = r.json()
    assert "status" in data
    assert "checks" in data
    for dep in ("postgres", "redis", "qdrant"):
        assert dep in data["checks"]
