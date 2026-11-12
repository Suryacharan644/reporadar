"""Small infrastructure helpers: TTL cache, per-client rate limiter, report storage."""

from __future__ import annotations

import secrets
import time
from collections import deque
from collections.abc import Callable
from typing import Any, Protocol

import httpx


class TTLCache:
    def __init__(self, ttl_seconds: float, clock: Callable[[], float] = time.monotonic) -> None:
        self._ttl = ttl_seconds
        self._clock = clock
        self._items: dict[str, tuple[float, Any]] = {}

    def get(self, key: str) -> Any | None:
        item = self._items.get(key)
        if item is None:
            return None
        expires, value = item
        if self._clock() >= expires:
            self._items.pop(key, None)
            return None
        return value

    def set(self, key: str, value: Any) -> None:
        self._items[key] = (self._clock() + self._ttl, value)

    def clear(self) -> None:
        self._items.clear()


class SlidingWindowLimiter:
    """Allow at most ``limit`` events per ``window`` seconds per key."""

    def __init__(self, limit: int, window: float = 60.0, clock: Callable[[], float] = time.monotonic) -> None:
        self._limit = limit
        self._window = window
        self._clock = clock
        self._hits: dict[str, deque[float]] = {}

    def hit(self, key: str) -> float | None:
        """Record a hit. Returns None if allowed, else seconds until a slot frees up."""
        now = self._clock()
        hits = self._hits.setdefault(key, deque())
        while hits and now - hits[0] >= self._window:
            hits.popleft()
        if len(hits) >= self._limit:
            return max(1.0, self._window - (now - hits[0]))
        hits.append(now)
        return None


class ReportStore(Protocol):
    async def save(self, report: dict[str, Any]) -> str: ...
    async def get(self, report_id: str) -> dict[str, Any] | None: ...
    async def aclose(self) -> None: ...


def new_report_id() -> str:
    return secrets.token_urlsafe(9)


class MemoryStore:
    """Process-local storage. Fine for development; reports vanish on restart."""

    def __init__(self) -> None:
        self._items: dict[str, dict[str, Any]] = {}

    async def save(self, report: dict[str, Any]) -> str:
        report_id = new_report_id()
        self._items[report_id] = report
        return report_id

    async def get(self, report_id: str) -> dict[str, Any] | None:
        return self._items.get(report_id)

    async def aclose(self) -> None:
        return None


class SupabaseStore:
    """Persists shared reports in a Supabase table via PostgREST.

    Uses the service-role key, which must only ever live on the server. The
    table has row-level security enabled with no public policies (see
    ``supabase/schema.sql``), so the anon key cannot read or write it.
    """

    def __init__(self, url: str, service_key: str, transport: httpx.AsyncBaseTransport | None = None) -> None:
        self._http = httpx.AsyncClient(
            base_url=url.rstrip("/") + "/rest/v1",
            headers={
                "apikey": service_key,
                "Authorization": f"Bearer {service_key}",
                "Content-Type": "application/json",
            },
            timeout=httpx.Timeout(10.0),
            transport=transport,
        )

    async def save(self, report: dict[str, Any]) -> str:
        report_id = new_report_id()
        repo = report["repo"]
        row = {
            "id": report_id,
            "repo_full_name": repo["full_name"],
            "score": report["score"],
            "grade": report["grade"],
            "report": report,
        }
        resp = await self._http.post("/reports", json=row, headers={"Prefer": "return=minimal"})
        resp.raise_for_status()
        return report_id

    async def get(self, report_id: str) -> dict[str, Any] | None:
        resp = await self._http.get("/reports", params={"id": f"eq.{report_id}", "select": "report"})
        resp.raise_for_status()
        rows = resp.json()
        return rows[0]["report"] if rows else None

    async def aclose(self) -> None:
        await self._http.aclose()
