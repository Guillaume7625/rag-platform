"""Health check endpoint with dependency verification."""
from __future__ import annotations

import time

from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict:
    """Shallow health check — fast, for load balancers."""
    return {"status": "ok"}


@router.get("/health/ready")
def readiness() -> dict:
    """Deep health check — verifies all dependencies."""
    checks: dict[str, dict] = {}

    # Postgres
    try:
        from app.db.session import SessionLocal

        t = time.time()
        db = SessionLocal()
        db.execute("SELECT 1")  # type: ignore[arg-type]
        db.close()
        checks["postgres"] = {"status": "ok", "latency_ms": int((time.time() - t) * 1000)}
    except Exception as e:
        checks["postgres"] = {"status": "error", "detail": str(e)[:100]}

    # Redis
    try:
        import redis

        from app.core.config import settings

        t = time.time()
        r = redis.Redis.from_url(settings.redis_url)
        r.ping()
        r.close()
        checks["redis"] = {"status": "ok", "latency_ms": int((time.time() - t) * 1000)}
    except Exception as e:
        checks["redis"] = {"status": "error", "detail": str(e)[:100]}

    # Qdrant
    try:
        import httpx

        from app.core.config import settings

        t = time.time()
        resp = httpx.get(f"{settings.qdrant_url}/collections", timeout=5.0)
        checks["qdrant"] = {
            "status": "ok" if resp.status_code == 200 else "error",
            "latency_ms": int((time.time() - t) * 1000),
        }
    except Exception as e:
        checks["qdrant"] = {"status": "error", "detail": str(e)[:100]}

    all_ok = all(c["status"] == "ok" for c in checks.values())
    return {"status": "ok" if all_ok else "degraded", "checks": checks}
