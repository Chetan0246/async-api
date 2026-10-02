"""In-process sliding-window rate limiter (per-client) used as FastAPI dependency."""

from __future__ import annotations

import time
from collections import defaultdict, deque
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status

from app.config import get_settings


class SlidingWindowLimiter:
    def __init__(self, max_requests: int, window_seconds: float) -> None:
        self.max_requests = max_requests
        self.window = window_seconds
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._order: dict[str, float] = {}

    def _prune(self, key: str, now: float) -> None:
        q = self._hits[key]
        while q and now - q[0] >= self.window:
            q.popleft()

    def hit(self, key: str) -> tuple[bool, int]:
        """Record a hit; return (allowed, seconds_until_next_allowed)."""
        now = time.monotonic()
        self._prune(key, now)
        q = self._hits[key]
        if len(q) >= self.max_requests:
            retry_after = max(1, int(self.window - (now - q[0])) + 1)
            return False, retry_after
        q.append(now)
        self._order[key] = now
        return True, 0

    def sweep_idle(self, idle_after: float = 600.0) -> None:
        """Drop keys idle longer than `idle_after` seconds to bound memory."""
        now = time.monotonic()
        for key in [k for k, t in self._order.items() if now - t > idle_after]:
            self._hits.pop(key, None)
            self._order.pop(key, None)


_settings = get_settings()
limiter = SlidingWindowLimiter(_settings.rate_limit_requests, _settings.rate_limit_window_seconds)


def rate_limit(request: Request) -> None:
    client_ip = request.client.host if request.client else "anonymous"
    allowed, retry_after = limiter.hit(client_ip)
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded",
            headers={"Retry-After": str(retry_after)},
        )


RateLimited = Annotated[None, Depends(rate_limit)]
