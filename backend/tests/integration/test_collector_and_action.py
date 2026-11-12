"""Collector behaviour with partial GitHub failures, and the GitHub Action runner."""

import asyncio
import json
from datetime import timedelta

import httpx
import pytest

from app import action_runner
from app.collector import collect_snapshot
from app.github_client import GitHubClient, GitHubError, RateLimitError
from app.repo_input import RepoRef
from tests.helpers import FAKE_REPO, NOW, fake_github


def _run(coro):
    return asyncio.run(coro)


def test_secondary_failures_become_warnings_not_errors():
    healthy = fake_github()

    class FailCommits(httpx.AsyncBaseTransport):
        """Healthy fake GitHub, except the commits endpoint returns a 500."""

        async def handle_async_request(self, request):
            if request.url.path.endswith("/commits"):
                return httpx.Response(500, json={"message": "boom"})
            return await healthy.handle_async_request(request)

    Wrapper = FailCommits

    async def go():
        async with GitHubClient("t", transport=Wrapper()) as gh:
            return await collect_snapshot(gh, RepoRef("octo", "widget"), now=NOW)

    snapshot = _run(go())
    assert snapshot.commits == []
    assert any("Commits unavailable" in w for w in snapshot.warnings)
    assert snapshot.readme  # primary data still present


def test_rate_limit_is_not_swallowed_by_secondary_fetches():
    async def go():
        async with GitHubClient("t", transport=fake_github(rate_limited=True)) as gh:
            await collect_snapshot(gh, RepoRef("octo", "widget"), now=NOW)

    with pytest.raises(RateLimitError):
        _run(go())


def test_private_repository_is_rejected_by_collector():
    async def go():
        async with GitHubClient(None, transport=fake_github(repo={**FAKE_REPO, "private": True})) as gh:
            await collect_snapshot(gh, RepoRef("octo", "widget"), now=NOW)

    with pytest.raises(GitHubError) as exc:
        _run(go())
    assert exc.value.status_code == 404


def test_contributing_file_is_found_case_insensitively():
    paths = ["README.md", "LICENSE", "docs/contributing.md"]

    async def go():
        async with GitHubClient(None, transport=fake_github(paths=paths)) as gh:
            return await collect_snapshot(gh, RepoRef("octo", "widget"), now=NOW)

    snapshot = _run(go())
    assert snapshot.contributing is not None


def test_action_runner_writes_outputs_and_enforces_threshold(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    summary = tmp_path / "summary.md"
    event = tmp_path / "event.json"
    event.write_text(json.dumps({"pull_request": {"number": 5}}), encoding="utf-8")

    monkeypatch.setenv("GITHUB_REPOSITORY", "octo/widget")
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary))
    monkeypatch.setenv("GITHUB_EVENT_PATH", str(event))
    monkeypatch.setenv("REPORADAR_MIN_SCORE", "101")  # impossible: must fail
    monkeypatch.setenv("REPORADAR_COMMENT", "false")  # no network write in tests

    original = action_runner.GitHubClient

    def patched(token=None, **kwargs):
        return original(token, transport=fake_github(), **kwargs)

    monkeypatch.setattr(action_runner, "GitHubClient", patched)

    code = _run(action_runner.run())
    assert code == 1
    assert json.loads((tmp_path / "reporadar-report.json").read_text(encoding="utf-8"))["score"] >= 85
    assert "RepoRadar report" in summary.read_text(encoding="utf-8")


def test_action_runner_requires_github_repository(monkeypatch):
    monkeypatch.delenv("GITHUB_REPOSITORY", raising=False)
    assert _run(action_runner.run()) == 2
