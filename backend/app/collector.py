"""Collect a ``RepoSnapshot`` for a public repository from the GitHub REST API.

Primary data (repo metadata, the file tree and the README) is required: if it
fails the request fails. Secondary data (commits, issues, PRs, contributors,
workflow runs) is optional: a failure there is recorded as a warning and the
analysis continues with less evidence. Rate-limit errors are never swallowed.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from datetime import datetime, timezone
from typing import Any, TypeVar

from .analyzer import (
    CommitInfo,
    ContributorInfo,
    IssueInfo,
    PullInfo,
    RepoSnapshot,
    RunInfo,
)
from .github_client import GitHubClient, GitHubError, NotFoundError, RateLimitError
from .repo_input import RepoRef

T = TypeVar("T")
CONTRIBUTING_CANDIDATES = (".github/CONTRIBUTING.md", "CONTRIBUTING.md", "docs/CONTRIBUTING.md")


def parse_time(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


async def _optional(
    label: str, call: Callable[[], Awaitable[T]], default: T, warnings: list[str]
) -> T:
    """Run a secondary fetch; keep going on ordinary errors, but never on rate limits."""
    try:
        return await call()
    except RateLimitError:
        raise
    except GitHubError as exc:
        warnings.append(f"{label} unavailable: {exc.message}")
        return default


def _commit(raw: dict[str, Any]) -> CommitInfo:
    commit = raw.get("commit", {})
    author_info = commit.get("author") or {}
    login = (raw.get("author") or {}).get("login")
    message = (commit.get("message") or "").splitlines()[0][:140] if commit.get("message") else ""
    return CommitInfo(
        sha=(raw.get("sha") or "")[:7],
        message=message,
        author=login or author_info.get("name") or "unknown",
        date=parse_time(author_info.get("date")) or datetime.now(timezone.utc),
        url=raw.get("html_url"),
    )


def _issue(raw: dict[str, Any]) -> IssueInfo:
    return IssueInfo(
        number=raw["number"],
        title=raw.get("title", ""),
        state=raw.get("state", "open"),
        created_at=parse_time(raw.get("created_at")) or datetime.now(timezone.utc),
        closed_at=parse_time(raw.get("closed_at")),
        url=raw.get("html_url"),
        comments=raw.get("comments", 0),
    )


def _pull(raw: dict[str, Any]) -> PullInfo:
    return PullInfo(
        number=raw["number"],
        title=raw.get("title", ""),
        state=raw.get("state", "open"),
        created_at=parse_time(raw.get("created_at")) or datetime.now(timezone.utc),
        merged_at=parse_time(raw.get("merged_at")),
        url=raw.get("html_url"),
    )


def _run(raw: dict[str, Any]) -> RunInfo:
    return RunInfo(
        name=raw.get("name") or "workflow",
        status=raw.get("status") or "unknown",
        conclusion=raw.get("conclusion"),
        created_at=parse_time(raw.get("created_at")) or datetime.now(timezone.utc),
        url=raw.get("html_url"),
    )


async def collect_snapshot(
    client: GitHubClient, ref: RepoRef, now: datetime | None = None
) -> RepoSnapshot:
    fetched_at = now or datetime.now(timezone.utc)
    repo = await client.get_repo(ref.owner, ref.name)  # NotFoundError propagates

    if repo.get("private"):
        raise NotFoundError("This repository is private. RepoRadar only analyses public repositories.")

    branch = repo.get("default_branch") or "main"
    warnings: list[str] = []

    tree_task = _optional("File tree", lambda: client.get_tree(ref.owner, ref.name, branch), {}, warnings)
    readme_task = _optional("README", lambda: client.get_readme(ref.owner, ref.name), None, warnings)
    commits_task = _optional("Commits", lambda: client.list_commits(ref.owner, ref.name), [], warnings)
    issues_task = _optional("Issues", lambda: client.list_issues(ref.owner, ref.name), [], warnings)
    pulls_task = _optional("Pull requests", lambda: client.list_pulls(ref.owner, ref.name), [], warnings)
    contributors_task = _optional(
        "Contributors", lambda: client.list_contributors(ref.owner, ref.name), [], warnings
    )
    runs_task = _optional("Workflow runs", lambda: client.list_workflow_runs(ref.owner, ref.name), [], warnings)

    tree, readme, commits, issues, pulls, contributors, runs = await asyncio.gather(
        tree_task, readme_task, commits_task, issues_task, pulls_task, contributors_task, runs_task
    )

    paths = [entry["path"] for entry in tree.get("tree", []) if entry.get("type") in ("blob", "tree")]
    path_set = set(paths)
    contributing_path = next((p for p in CONTRIBUTING_CANDIDATES if p in path_set), None)
    if not contributing_path:
        # Case-insensitive fallback (e.g. contributing.md)
        contributing_path = next((p for p in paths if p.lower().endswith("contributing.md")), None)
    contributing = None
    if contributing_path:
        contributing = await _optional(
            "CONTRIBUTING file", lambda: client.get_text(f"/repos/{ref.owner}/{ref.name}/contents/{contributing_path}"),
            None, warnings,
        )

    issue_items = [i for i in issues if "pull_request" not in i]
    if tree.get("truncated"):
        warnings.append("The repository file tree is very large; some files may not have been inspected.")

    license_info = repo.get("license") or {}
    return RepoSnapshot(
        owner=ref.owner,
        name=repo.get("name", ref.name),
        html_url=repo.get("html_url", f"https://github.com/{ref.full_name}"),
        fetched_at=fetched_at,
        description=repo.get("description"),
        topics=list(repo.get("topics") or []),
        homepage=repo.get("homepage") or None,
        license_spdx=license_info.get("spdx_id"),
        stars=repo.get("stargazers_count", 0),
        forks=repo.get("forks_count", 0),
        open_issues=repo.get("open_issues_count", 0),
        language=repo.get("language"),
        default_branch=branch,
        pushed_at=parse_time(repo.get("pushed_at")),
        created_at=parse_time(repo.get("created_at")),
        archived=bool(repo.get("archived")),
        private=False,
        paths=paths,
        tree_truncated=bool(tree.get("truncated")),
        readme=readme,
        contributing=contributing,
        commits=[_commit(c) for c in commits],
        issues=[_issue(i) for i in issue_items],
        pulls=[_pull(p) for p in pulls],
        contributors=[
            ContributorInfo(
                login=c.get("login", "unknown"),
                contributions=c.get("contributions", 0),
                url=c.get("html_url"),
                avatar_url=c.get("avatar_url"),
            )
            for c in contributors
            if c.get("type", "User") == "User"
        ],
        runs=[_run(r) for r in runs],
        warnings=warnings,
    )
