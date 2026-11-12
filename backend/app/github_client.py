"""Thin async wrapper around the GitHub REST API.

Only public, read-only endpoints are used (plus comment creation for the
GitHub Action). Rate-limit responses are converted to ``RateLimitError`` so the
API layer can return a 429 with a Retry-After hint instead of a generic failure.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any
from urllib.parse import quote

import httpx

API_BASE = "https://api.github.com"
API_VERSION = "2022-11-28"
RAW_ACCEPT = "application/vnd.github.raw"


class GitHubError(Exception):
    status_code = 502

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.message = message
        if status_code is not None:
            self.status_code = status_code


class NotFoundError(GitHubError):
    status_code = 404

    def __init__(self, message: str = "Repository not found or not public.") -> None:
        super().__init__(message, 404)


class RateLimitError(GitHubError):
    status_code = 429

    def __init__(self, message: str, reset_at: int | None, retry_after: int | None) -> None:
        super().__init__(message, 429)
        self.reset_at = reset_at
        self.retry_after = retry_after


class GitHubClient:
    """Async client. Use as ``async with GitHubClient(token) as gh: ...``."""

    def __init__(
        self,
        token: str | None = None,
        *,
        base_url: str = API_BASE,
        transport: httpx.AsyncBaseTransport | None = None,
        clock: Callable[[], float] = time.time,
    ) -> None:
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": API_VERSION,
            "User-Agent": "RepoRadar",
        }
        if token:
            headers["Authorization"] = f"Bearer {token}"
        self._http = httpx.AsyncClient(
            base_url=base_url,
            headers=headers,
            timeout=httpx.Timeout(15.0),
            transport=transport,
        )
        self._clock = clock

    async def __aenter__(self) -> "GitHubClient":
        return self

    async def __aexit__(self, *exc_info: object) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        await self._http.aclose()

    # ------------------------------------------------------------------ core

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json: Any = None,
        accept: str | None = None,
    ) -> httpx.Response:
        headers = {"Accept": accept} if accept else None
        try:
            resp = await self._http.request(method, path, params=params, json=json, headers=headers)
        except httpx.HTTPError as exc:
            raise GitHubError(
                "The RepoRadar server could not reach api.github.com "
                f"({exc.__class__.__name__}). Check that the machine running the backend has internet "
                "access and is not blocked by a firewall or proxy.",
                502,
            ) from exc
        self._raise_for_status(resp)
        return resp

    def _raise_for_status(self, resp: httpx.Response) -> None:
        if resp.status_code < 400:
            return
        remaining = resp.headers.get("X-RateLimit-Remaining")
        reset_raw = resp.headers.get("X-RateLimit-Reset")
        retry_raw = resp.headers.get("Retry-After")
        reset_at = int(reset_raw) if reset_raw and reset_raw.isdigit() else None
        retry_after = int(retry_raw) if retry_raw and retry_raw.isdigit() else None

        is_rate_limited = resp.status_code == 429 or (
            resp.status_code == 403 and (remaining == "0" or retry_after is not None)
        )
        if is_rate_limited:
            if retry_after is None and reset_at is not None:
                retry_after = max(0, reset_at - int(self._clock()))
            wait = "a few minutes" if retry_after is None else f"about {max(1, -(-retry_after // 60))} minute(s)"
            raise RateLimitError(
                f"GitHub API rate limit reached. Try again in {wait}.",
                reset_at=reset_at,
                retry_after=retry_after,
            )
        if resp.status_code == 404:
            raise NotFoundError()
        raise GitHubError(f"GitHub API returned HTTP {resp.status_code}.", 502)

    async def get_json(self, path: str, params: dict[str, Any] | None = None) -> Any:
        return (await self._request("GET", path, params=params)).json()

    async def get_text(self, path: str) -> str | None:
        """Raw file contents, or ``None`` when the file does not exist."""
        try:
            return (await self._request("GET", path, accept=RAW_ACCEPT)).text
        except NotFoundError:
            return None

    async def post_json(self, path: str, body: dict[str, Any]) -> Any:
        return (await self._request("POST", path, json=body)).json()

    async def patch_json(self, path: str, body: dict[str, Any]) -> Any:
        return (await self._request("PATCH", path, json=body)).json()

    # ------------------------------------------------------- repo endpoints

    async def get_repo(self, owner: str, name: str) -> dict[str, Any]:
        return await self.get_json(f"/repos/{owner}/{name}")

    async def get_tree(self, owner: str, name: str, ref: str) -> dict[str, Any]:
        return await self.get_json(
            f"/repos/{owner}/{name}/git/trees/{quote(ref, safe='')}", params={"recursive": "1"}
        )

    async def get_readme(self, owner: str, name: str) -> str | None:
        try:
            return (await self._request("GET", f"/repos/{owner}/{name}/readme", accept=RAW_ACCEPT)).text
        except NotFoundError:
            return None

    async def list_commits(self, owner: str, name: str, per_page: int = 30) -> list[dict[str, Any]]:
        return await self.get_json(f"/repos/{owner}/{name}/commits", params={"per_page": per_page})

    async def list_issues(self, owner: str, name: str, per_page: int = 30) -> list[dict[str, Any]]:
        return await self.get_json(
            f"/repos/{owner}/{name}/issues",
            params={"state": "all", "per_page": per_page, "sort": "updated", "direction": "desc"},
        )

    async def list_pulls(self, owner: str, name: str, per_page: int = 30) -> list[dict[str, Any]]:
        return await self.get_json(
            f"/repos/{owner}/{name}/pulls",
            params={"state": "all", "per_page": per_page, "sort": "updated", "direction": "desc"},
        )

    async def list_contributors(self, owner: str, name: str, per_page: int = 10) -> list[dict[str, Any]]:
        return await self.get_json(f"/repos/{owner}/{name}/contributors", params={"per_page": per_page})

    async def list_workflow_runs(self, owner: str, name: str, per_page: int = 5) -> list[dict[str, Any]]:
        data = await self.get_json(f"/repos/{owner}/{name}/actions/runs", params={"per_page": per_page})
        return list(data.get("workflow_runs", []))

    async def search_issues(self, query: str, page: int = 1, per_page: int = 20) -> dict[str, Any]:
        return await self.get_json(
            "/search/issues", params={"q": query, "page": page, "per_page": per_page, "sort": "updated"}
        )

    # ----------------------------------------------------- comment endpoints

    async def list_issue_comments(self, owner: str, name: str, number: int) -> list[dict[str, Any]]:
        return await self.get_json(f"/repos/{owner}/{name}/issues/{number}/comments", params={"per_page": 100})

    async def create_comment(self, owner: str, name: str, number: int, body: str) -> dict[str, Any]:
        return await self.post_json(f"/repos/{owner}/{name}/issues/{number}/comments", {"body": body})

    async def update_comment(self, owner: str, name: str, comment_id: int, body: str) -> dict[str, Any]:
        return await self.patch_json(f"/repos/{owner}/{name}/issues/comments/{comment_id}", {"body": body})
