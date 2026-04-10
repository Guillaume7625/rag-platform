"""Simple in-memory sliding-window rate limiter.

Used to protect /auth/login from brute-force attempts. For multi-process
deployments (--workers > 1) each process maintains its own counter, which
is acceptable: the effective limit becomes N × workers. For strict global
limits, swap to a Redis-backed implementation.
"""
from __future__ import annotations

import time
from collections import defaultdict
from threading import Lock

from fastapi import HTTPException, Request, status


class RateLimiter:
    def __init__(self, max_requests: int = 10, window_seconds: int = 60) -> None:
        self.max_requests = max_requests
        self.window = window_seconds
        self._hits: dict[str, list[float]] = defaultdict(list)
        self._lock = Lock()

    def _client_key(self, request: Request) -> str:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"

    def check(self, request: Request) -> None:
        key = self._client_key(request)
        now = time.monotonic()
        with self._lock:
            hits = self._hits[key]
            # Prune expired entries.
            cutoff = now - self.window
            self._hits[key] = hits = [t for t in hits if t > cutoff]
            if len(hits) >= self.max_requests:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"too many requests, retry after {self.window}s",
                )
            hits.append(now)


# 10 login attempts per minute per IP.
login_limiter = RateLimiter(max_requests=10, window_seconds=60)

