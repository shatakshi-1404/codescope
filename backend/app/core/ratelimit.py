"""
Small in-memory rate limiter for the sign-in endpoints.

Why it exists: behind nginx (Docker setup) the proxy throttles /api/auth/*. On hosts with no
proxy of ours in front (Render), the app has to do it itself.

Honest limits: the counters live in this process, which fits the single-process design of
CodeScope (see README). They reset on restart, and each instance counts separately.
"""
import threading
import time
from collections import deque

from fastapi import Request

from app.core.config import settings
from app.core.errors import TooManyRequestsError


class SlidingWindowLimiter:
    def __init__(self, window_seconds: float = 60.0, max_keys: int = 10_000, clock=time.monotonic):
        self._clock = clock
        self._window = window_seconds
        self._max_keys = max_keys
        self._hits: dict[str, deque[float]] = {}
        self._lock = threading.Lock()

    def allow(self, key: str, limit: int) -> bool:
        """Records one hit and returns True, or returns False when `key` is over `limit`."""
        if limit <= 0:
            return True
        now = self._clock()
        with self._lock:
            hits = self._hits.get(key)
            if hits is None:
                if len(self._hits) >= self._max_keys:
                    self._make_room(now)
                hits = self._hits[key] = deque()
            cutoff = now - self._window
            while hits and hits[0] <= cutoff:
                hits.popleft()
            if len(hits) >= limit:
                return False
            hits.append(now)
            return True

    def _make_room(self, now: float) -> None:
        cutoff = now - self._window
        for k in [k for k, h in self._hits.items() if not h or h[-1] <= cutoff]:
            del self._hits[k]
        if len(self._hits) >= self._max_keys:  # still full: drop the oldest key
            del self._hits[next(iter(self._hits))]

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()


auth_limiter = SlidingWindowLimiter()

_MESSAGE = "Too many attempts. Please wait a minute and try again."


def client_ip(request: Request) -> str:
    """
    The caller's IP. When a proxy such as Render's router sits in front, it APPENDS the address it
    saw to X-Forwarded-For, so the LAST entry is the trustworthy one. The first entries can be
    forged by the client, so they are never used.
    """
    forwarded = request.headers.get("x-forwarded-for", "")
    last = forwarded.split(",")[-1].strip() if forwarded else ""
    if last:
        return last
    return request.client.host if request.client else "unknown"


def enforce_ip_limit(request: Request) -> None:
    """FastAPI dependency for the public auth endpoints."""
    if not auth_limiter.allow(f"ip:{client_ip(request)}", settings.auth_rate_limit_per_minute):
        raise TooManyRequestsError(_MESSAGE)


def enforce_email_limit(action: str, email: str) -> None:
    """
    Per-account throttle. This is the real brute-force defence: it holds no matter how many
    IP addresses an attacker uses.
    """
    limit = settings.auth_rate_limit_per_minute
    per_email = max(3, limit // 3) if limit > 0 else 0
    if not auth_limiter.allow(f"{action}:{email.strip().lower()}", per_email):
        raise TooManyRequestsError(_MESSAGE)
