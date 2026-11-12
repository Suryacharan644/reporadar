"""Integration tests: the real FastAPI app, with GitHub replaced by an httpx MockTransport."""

from fastapi.testclient import TestClient

from app.config import Settings
from app.infra import MemoryStore
from app.main import create_app
from tests.helpers import FAKE_REPO, fake_github


def client(transport=None, **settings) -> TestClient:
    cfg = Settings(rate_limit_per_minute=settings.pop("rate_limit", 100), **settings)
    app = create_app(cfg, transport=transport or fake_github(), store=MemoryStore())
    return TestClient(app)


def test_health_reports_configuration_without_secrets():
    body = client().get("/api/health").json()
    assert body["status"] == "ok"
    assert body["github_token_configured"] is False
    assert "token" not in str(body).lower().replace("github_token_configured", "")


def test_validate_accepts_url_and_returns_metadata():
    resp = client().get("/api/validate", params={"repo": "https://github.com/octo/widget"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["valid"] is True
    assert body["full_name"] == "octo/widget"
    assert body["stars"] == FAKE_REPO["stargazers_count"]


def test_validate_rejects_garbage_with_400():
    resp = client().get("/api/validate", params={"repo": "not a repo"})
    assert resp.status_code == 400
    assert "error" in resp.json()


def test_unknown_or_private_repository_returns_404():
    resp = client(fake_github(repo_missing=True)).get("/api/repos/octo/widget/report")
    assert resp.status_code == 404
    assert "not found or not public" in resp.json()["error"]


def test_private_repository_is_refused_even_if_returned():
    private = {**FAKE_REPO, "private": True}
    resp = client(fake_github(repo=private)).get("/api/repos/octo/widget/report")
    assert resp.status_code == 404
    assert "private" in resp.json()["error"]


def test_full_report_end_to_end():
    resp = client().get("/api/repos/octo/widget/report")
    assert resp.status_code == 200
    report = resp.json()
    assert report["repo"]["full_name"] == "octo/widget"
    assert 0 <= report["score"] <= 100
    assert report["score"] >= 85
    check_ids = {c["id"] for c in report["checks"]}
    assert "readme.exists" in check_ids and "activity.recency" in check_ids
    assert report["stats"]["recent_commits"][0]["sha"] == "abcdef1"
    assert report["stats"]["contributors"][0]["login"] == "maintainer"


def test_bare_repository_report_has_critical_findings():
    transport = fake_github(paths=["index.js"], readme=None, contributing=None)
    report = client(transport).get("/api/repos/octo/widget/report").json()
    assert report["score"] < 50
    assert report["summary"]["critical"] >= 3
    critical = [c for c in report["checks"] if c["severity"] == "critical"]
    assert all(c["recommendation"] for c in critical)


def test_rate_limit_from_github_becomes_429_with_retry_after():
    resp = client(fake_github(rate_limited=True)).get("/api/repos/octo/widget/report")
    assert resp.status_code == 429
    assert int(resp.headers["Retry-After"]) > 0
    assert "rate limit" in resp.json()["error"].lower()


def test_reports_are_cached_between_requests():
    calls: list[str] = []
    c = client(fake_github(calls=calls))
    c.get("/api/repos/octo/widget/report")
    first = len(calls)
    c.get("/api/repos/octo/widget/report")
    assert len(calls) == first  # second request served from cache


def test_generate_returns_files():
    body = client().get("/api/repos/octo/widget/generate/readme").json()
    assert body["kind"] == "readme"
    assert body["files"][0]["path"] == "README.md"
    issue = client().get("/api/repos/octo/widget/generate/issue-templates").json()
    assert {f["path"] for f in issue["files"]} >= {".github/ISSUE_TEMPLATE/bug_report.md"}


def test_generate_unknown_kind_is_404():
    assert client().get("/api/repos/octo/widget/generate/nope").status_code == 404


def test_badge_is_svg():
    resp = client().get("/api/repos/octo/widget/badge.svg")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("image/svg+xml")
    assert "/100" in resp.text


def test_share_report_round_trip():
    c = client()
    created = c.post("/api/reports", json={"repo": "octo/widget"})
    assert created.status_code == 201
    report_id = created.json()["id"]
    fetched = c.get(f"/api/reports/{report_id}")
    assert fetched.status_code == 200
    assert fetched.json()["repo"]["full_name"] == "octo/widget"


def test_unknown_share_id_is_404_and_bad_id_is_404():
    c = client()
    assert c.get("/api/reports/doesnotexist123").status_code == 404
    assert c.get("/api/reports/!!").status_code == 404


def test_contributions_filters_and_sanitises_query():
    items = [
        {
            "title": "Add docs",
            "number": 3,
            "html_url": "https://github.com/octo/widget/issues/3",
            "repository_url": "https://api.github.com/repos/octo/widget",
            "comments": 0,
            "created_at": "2026-01-01T00:00:00Z",
            "updated_at": "2026-01-02T00:00:00Z",
            "labels": [{"name": "good first issue"}],
        }
    ]
    c = client(fake_github(search_items=items))
    body = c.get("/api/contributions", params={"label": "good first issue", "q": 'readme" OR repo:x'}).json()
    assert body["items"][0]["repo"] == "octo/widget"
    assert body["items"][0]["labels"] == ["good first issue"]
    assert c.get("/api/contributions", params={"label": "drop table"}).status_code == 400


def test_post_reports_rejects_empty_body():
    assert client().post("/api/reports", json={"repo": ""}).status_code == 422
