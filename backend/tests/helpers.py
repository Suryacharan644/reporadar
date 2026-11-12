"""Shared fixtures: a fully healthy synthetic repository and a fake GitHub API."""

from __future__ import annotations

import json
import time
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx

from app.analyzer import (
    CommitInfo,
    ContributorInfo,
    IssueInfo,
    PullInfo,
    RepoSnapshot,
    RunInfo,
)

NOW = datetime(2026, 11, 12, 12, 0, tzinfo=timezone.utc)

HEALTHY_README = """# Widget

Widget is a small library for building reliable widgets in Python. It supports
streaming, batching and retries out of the box, and it is designed for teams that
need predictable behaviour under load.

## Features

- Fast batching
- Automatic retries with jitter
- Typed public API

## Installation

```bash
pip install widget
```

## Usage

```python
from widget import Widget
w = Widget()
w.run()
```

## License

MIT. See LICENSE.
""" + ("Extra explanatory text to make the README comprehensive. " * 12)

HEALTHY_CONTRIBUTING = """# Contributing

## Setting up your environment
Install the dependencies with pip install -e .

## Running tests
Run pytest before you push.

## Pull requests
Open a pull request against main and fill in the template.

## Style
Follow the lint and format rules. Use clear commit messages.
"""

HEALTHY_PATHS = [
    "LICENSE",
    "README.md",
    "CONTRIBUTING.md",
    "pyproject.toml",
    "poetry.lock",
    "pytest.ini",
    "docs/index.md",
    "src/widget/__init__.py",
    ".github/ISSUE_TEMPLATE/bug_report.md",
    ".github/ISSUE_TEMPLATE/feature_request.md",
    ".github/PULL_REQUEST_TEMPLATE.md",
    ".github/workflows/ci.yml",
    ".github/dependabot.yml",
    "tests/test_widget.py",
    "tests/test_batch.py",
    "tests/test_retry.py",
    "tests/test_api.py",
    "tests/test_cli.py",
    "tests/test_utils.py",
]


def _commit(i: int, when: datetime) -> CommitInfo:
    return CommitInfo(
        sha=f"abc{i:04d}",
        message=f"Change {i}",
        author="maintainer",
        date=when,
        url=f"https://github.com/octo/widget/commit/{i}",
    )


def healthy_snapshot(**overrides: Any) -> RepoSnapshot:
    """A repository that should pass every check."""
    issues = [
        IssueInfo(number=i, title=f"Issue {i}", state="closed", created_at=NOW - timedelta(days=i),
                  closed_at=NOW - timedelta(days=i - 1), url=None, comments=2)
        for i in range(1, 11)
    ]
    snapshot = RepoSnapshot(
        owner="octo",
        name="widget",
        html_url="https://github.com/octo/widget",
        fetched_at=NOW,
        description="A small library for building reliable widgets",
        topics=["widgets", "python"],
        homepage="https://widget.example.org",
        license_spdx="MIT",
        stars=420,
        forks=40,
        open_issues=0,
        language="Python",
        default_branch="main",
        pushed_at=NOW - timedelta(days=2),
        created_at=NOW - timedelta(days=900),
        paths=list(HEALTHY_PATHS),
        readme=HEALTHY_README,
        contributing=HEALTHY_CONTRIBUTING,
        commits=[_commit(i, NOW - timedelta(days=i * 3)) for i in range(12)],
        issues=issues,
        pulls=[
            PullInfo(number=i, title=f"PR {i}", state="closed", created_at=NOW - timedelta(days=i),
                     merged_at=NOW - timedelta(days=i - 0.5), url=None)
            for i in range(1, 6)
        ],
        contributors=[ContributorInfo("maintainer", 300, None, None)],
        runs=[RunInfo("CI", "completed", "success", NOW - timedelta(hours=3), None)],
    )
    for key, value in overrides.items():
        setattr(snapshot, key, value)
    return snapshot


def bare_snapshot(**overrides: Any) -> RepoSnapshot:
    """A repository with almost nothing in it."""
    snapshot = RepoSnapshot(
        owner="octo",
        name="empty",
        html_url="https://github.com/octo/empty",
        fetched_at=NOW,
        pushed_at=NOW - timedelta(days=800),
        paths=["index.js"],
    )
    for key, value in overrides.items():
        setattr(snapshot, key, value)
    return snapshot


# --------------------------------------------------------------- fake GitHub

FAKE_REPO: dict[str, Any] = {
    "name": "widget",
    "full_name": "octo/widget",
    "html_url": "https://github.com/octo/widget",
    "description": "A small library for building reliable widgets",
    "topics": ["widgets", "python"],
    "homepage": "https://widget.example.org",
    "license": {"spdx_id": "MIT"},
    "stargazers_count": 420,
    "forks_count": 40,
    "open_issues_count": 0,
    "language": "Python",
    "default_branch": "main",
    "pushed_at": (NOW - timedelta(days=2)).isoformat().replace("+00:00", "Z"),
    "created_at": (NOW - timedelta(days=900)).isoformat().replace("+00:00", "Z"),
    "archived": False,
    "private": False,
}


def _json(payload: Any, status: int = 200) -> httpx.Response:
    return httpx.Response(status, json=payload)


def fake_github(
    *,
    repo: dict[str, Any] | None = None,
    paths: list[str] | None = None,
    readme: str | None = HEALTHY_README,
    contributing: str | None = HEALTHY_CONTRIBUTING,
    rate_limited: bool = False,
    repo_missing: bool = False,
    search_items: list[dict[str, Any]] | None = None,
    calls: list[str] | None = None,
) -> httpx.MockTransport:
    """An ``httpx.MockTransport`` that mimics the GitHub REST endpoints RepoRadar uses."""
    repo_payload = repo if repo is not None else FAKE_REPO
    tree_paths = paths if paths is not None else HEALTHY_PATHS

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if calls is not None:
            calls.append(path)
        if rate_limited:
            reset = int(time.time()) + 120
            return httpx.Response(
                403,
                json={"message": "API rate limit exceeded"},
                headers={"X-RateLimit-Remaining": "0", "X-RateLimit-Reset": str(reset)},
            )
        if path == "/repos/octo/widget":
            return httpx.Response(404, json={"message": "Not Found"}) if repo_missing else _json(repo_payload)
        if path == "/repos/octo/widget/git/trees/main":
            return _json({"tree": [{"path": p, "type": "blob"} for p in tree_paths], "truncated": False})
        if path == "/repos/octo/widget/readme":
            if readme is None:
                return httpx.Response(404, json={"message": "Not Found"})
            return httpx.Response(200, text=readme)
        if path.startswith("/repos/octo/widget/contents/"):
            if contributing is None:
                return httpx.Response(404, json={"message": "Not Found"})
            return httpx.Response(200, text=contributing)
        if path == "/repos/octo/widget/commits":
            return _json([{"sha": "abcdef1234", "commit": {"message": "Ship it\n\nbody",
                           "author": {"name": "M", "date": (NOW - timedelta(days=1)).isoformat()}},
                           "author": {"login": "maintainer"}, "html_url": "https://github.com/c/1"}])
        if path == "/repos/octo/widget/issues":
            return _json([{"number": 1, "title": "Bug", "state": "closed",
                           "created_at": (NOW - timedelta(days=3)).isoformat(),
                           "closed_at": (NOW - timedelta(days=2)).isoformat(), "comments": 1}])
        if path == "/repos/octo/widget/pulls":
            return _json([{"number": 7, "title": "Add retries", "state": "closed",
                           "created_at": (NOW - timedelta(days=4)).isoformat(),
                           "merged_at": (NOW - timedelta(days=3)).isoformat()}])
        if path == "/repos/octo/widget/contributors":
            return _json([{"login": "maintainer", "contributions": 300, "type": "User"}])
        if path == "/repos/octo/widget/actions/runs":
            return _json({"workflow_runs": [{"name": "CI", "status": "completed", "conclusion": "success",
                                             "created_at": (NOW - timedelta(hours=1)).isoformat()}]})
        if path == "/search/issues":
            items = search_items if search_items is not None else []
            return _json({"total_count": len(items), "items": items})
        return httpx.Response(404, json={"message": "Not Found"})

    return httpx.MockTransport(handler)


def dumps(obj: Any) -> str:
    return json.dumps(obj)
