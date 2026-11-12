"""FastAPI application: the analysis API consumed by the Next.js frontend.

Endpoints
---------
GET  /api/health
GET  /api/validate?repo=owner/name          instant repository validation
GET  /api/repos/{owner}/{name}/report       full health report (cached)
GET  /api/repos/{owner}/{name}/generate/{kind}
GET  /api/repos/{owner}/{name}/badge.svg
POST /api/reports                           create a shareable report
GET  /api/reports/{id}                      read a shareable report
GET  /api/contributions?label=&q=&page=     beginner-friendly open issues

Every GitHub call happens here, on the server. The GitHub token never leaves it.
"""

from __future__ import annotations

import re
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, Field

from . import __version__
from .analyzer import CATEGORIES, CHECKS, METHODOLOGY_VERSION, RepoSnapshot
from .collector import collect_snapshot
from .config import Settings
from .generators import GENERATORS
from .github_client import GitHubClient, GitHubError, RateLimitError
from .infra import MemoryStore, ReportStore, SlidingWindowLimiter, SupabaseStore, TTLCache
from .repo_input import InvalidRepoInput, RepoRef, parse_repo_input
from .report import build_report, render_badge

ALLOWED_LABELS = {"good first issue", "help wanted", "beginner", "first-timers-only", "easy"}
REPORT_ID_RE = re.compile(r"^[A-Za-z0-9_-]{6,64}$")
GITHUB_OWNER_PREFIX = "https://api.github.com/repos/"


class ReportCreate(BaseModel):
    repo: str = Field(min_length=3, max_length=300)


def _client_ip(request: Request, trust_proxy: bool) -> str:
    if trust_proxy:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _sanitize_query(text: str) -> str:
    # Quotes and colons would let a user inject extra search qualifiers.
    return re.sub(r'["\:]', " ", text).strip()[:120]


def create_app(
    settings: Settings | None = None,
    *,
    transport: Any = None,
    store: ReportStore | None = None,
) -> FastAPI:
    """Application factory. ``transport`` lets tests stub GitHub with ``httpx.MockTransport``."""
    settings = settings or Settings.from_env()
    cache = TTLCache(settings.cache_ttl_seconds)
    limiter = SlidingWindowLimiter(settings.rate_limit_per_minute)
    if store is None:
        if settings.persistence_enabled:
            store = SupabaseStore(settings.supabase_url or "", settings.supabase_service_key or "")
        else:
            store = MemoryStore()

    app = FastAPI(title="RepoRadar API", version=__version__)
    app.state.store = store
    app.state.cache = cache
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.allowed_origins),
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
    )

    # ------------------------------------------------------------ helpers

    def github() -> GitHubClient:
        return GitHubClient(settings.github_token, transport=transport)

    def enforce_limit(request: Request) -> None:
        retry = limiter.hit(_client_ip(request, settings.trust_proxy))
        if retry is not None:
            raise HTTPException(
                status_code=429,
                detail="Too many analyses from your network. Please wait a moment and try again.",
                headers={"Retry-After": str(int(retry) + 1)},
            )

    async def load_snapshot(ref: RepoRef) -> RepoSnapshot:
        key = f"snapshot:{ref.full_name.lower()}"
        cached = cache.get(key)
        if cached is not None:
            return cached
        async with github() as gh:
            snapshot = await collect_snapshot(gh, ref)
        cache.set(key, snapshot)
        return snapshot

    # ------------------------------------------------------------ errors

    @app.exception_handler(GitHubError)
    async def _github_error(_: Request, exc: GitHubError) -> JSONResponse:
        headers: dict[str, str] = {}
        if isinstance(exc, RateLimitError) and exc.retry_after is not None:
            headers["Retry-After"] = str(exc.retry_after)
        return JSONResponse({"error": exc.message}, status_code=exc.status_code, headers=headers)

    @app.exception_handler(InvalidRepoInput)
    async def _invalid_input(_: Request, exc: InvalidRepoInput) -> JSONResponse:
        return JSONResponse({"error": str(exc)}, status_code=400)

    # ------------------------------------------------------------ routes

    @app.get("/api/health")
    async def health() -> dict[str, Any]:
        return {
            "status": "ok",
            "version": __version__,
            "github_token_configured": bool(settings.github_token),
            "persistence": "supabase" if settings.persistence_enabled else "memory",
        }

    @app.get("/api/methodology")
    async def methodology() -> dict[str, Any]:
        """The scoring rules themselves, so the public methodology page never drifts from the code."""
        return {
            "methodology_version": METHODOLOGY_VERSION,
            "categories": [{"id": cid, "title": title, "weight": weight} for cid, title, weight in CATEGORIES],
            "checks": [
                {
                    "id": c.id,
                    "category": c.category,
                    "title": c.title,
                    "max_points": c.max_points,
                    "critical_if_missing": c.critical,
                    "recommendation": c.recommendation,
                }
                for c in CHECKS
            ],
            "grades": {"A": ">= 90", "B": ">= 75", "C": ">= 60", "D": ">= 40", "F": "< 40"},
            "partial_credit": "A partial result earns half of a check's points, rounded down.",
        }

    @app.get("/api/validate")
    async def validate(repo: str, request: Request) -> dict[str, Any]:
        ref = parse_repo_input(repo)
        key = f"meta:{ref.full_name.lower()}"
        cached = cache.get(key)
        if cached is not None:
            return cached
        enforce_limit(request)
        async with github() as gh:
            meta = await gh.get_repo(ref.owner, ref.name)
        result = {
            "valid": True,
            "full_name": meta.get("full_name", ref.full_name),
            "description": meta.get("description"),
            "stars": meta.get("stargazers_count", 0),
            "language": meta.get("language"),
            "private": bool(meta.get("private")),
            "archived": bool(meta.get("archived")),
            "default_branch": meta.get("default_branch"),
        }
        cache.set(key, result)
        return result

    @app.get("/api/repos/{owner}/{name}/report")
    async def report(owner: str, name: str, request: Request) -> dict[str, Any]:
        ref = parse_repo_input(f"{owner}/{name}")
        enforce_limit(request)
        return build_report(await load_snapshot(ref))

    @app.get("/api/repos/{owner}/{name}/generate/{kind}")
    async def generate(owner: str, name: str, kind: str, request: Request) -> dict[str, Any]:
        if kind not in GENERATORS:
            raise HTTPException(status_code=404, detail=f"Unknown template '{kind}'.")
        ref = parse_repo_input(f"{owner}/{name}")
        enforce_limit(request)
        snapshot = await load_snapshot(ref)
        return {"kind": kind, "files": GENERATORS[kind](snapshot)}

    @app.get("/api/repos/{owner}/{name}/badge.svg")
    async def badge(owner: str, name: str, request: Request) -> Response:
        ref = parse_repo_input(f"{owner}/{name}")
        enforce_limit(request)
        score = build_report(await load_snapshot(ref))["score"]
        return Response(
            content=render_badge(ref.owner, ref.name, score),
            media_type="image/svg+xml",
            headers={"Cache-Control": "public, max-age=900"},
        )

    @app.post("/api/reports", status_code=201)
    async def create_report(body: ReportCreate, request: Request) -> dict[str, Any]:
        ref = parse_repo_input(body.repo)
        enforce_limit(request)
        document = build_report(await load_snapshot(ref))
        report_id = await app.state.store.save(document)
        return {"id": report_id, "path": f"/report/{report_id}"}

    @app.get("/api/reports/{report_id}")
    async def get_report(report_id: str) -> dict[str, Any]:
        if not REPORT_ID_RE.match(report_id):
            raise HTTPException(status_code=404, detail="Report not found.")
        document = await app.state.store.get(report_id)
        if document is None:
            raise HTTPException(status_code=404, detail="Report not found.")
        return document

    @app.get("/api/contributions")
    async def contributions(request: Request, label: str = "good first issue", q: str = "", page: int = 1) -> dict[str, Any]:
        if label not in ALLOWED_LABELS:
            raise HTTPException(status_code=400, detail=f"Label must be one of: {', '.join(sorted(ALLOWED_LABELS))}.")
        page = min(max(page, 1), 10)
        term = _sanitize_query(q)
        key = f"contrib:{label}:{term.lower()}:{page}"
        cached = cache.get(key)
        if cached is not None:
            return cached
        enforce_limit(request)
        query = f'label:"{label}" is:issue is:open archived:false'
        if term:
            query += f" {term} in:title,body"
        async with github() as gh:
            raw = await gh.search_issues(query, page=page, per_page=20)
        items = [
            {
                "title": item.get("title"),
                "number": item.get("number"),
                "url": item.get("html_url"),
                "repo": (item.get("repository_url") or "").replace(GITHUB_OWNER_PREFIX, ""),
                "comments": item.get("comments", 0),
                "created_at": item.get("created_at"),
                "updated_at": item.get("updated_at"),
                "labels": [lbl.get("name") for lbl in item.get("labels", []) if isinstance(lbl, dict)],
            }
            for item in raw.get("items", [])
        ]
        result = {"label": label, "total_count": raw.get("total_count", 0), "page": page, "items": items}
        cache.set(key, result)
        return result

    return app


# Module-level instance for `uvicorn app.main:app`.
app = create_app()
