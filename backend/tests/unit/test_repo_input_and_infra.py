import pytest

from app.infra import SlidingWindowLimiter, TTLCache
from app.repo_input import InvalidRepoInput, parse_repo_input


@pytest.mark.parametrize(
    "raw, owner, name",
    [
        ("octocat/Hello-World", "octocat", "Hello-World"),
        ("  octocat/hello.world  ", "octocat", "hello.world"),
        ("https://github.com/octocat/Hello-World", "octocat", "Hello-World"),
        ("https://github.com/octocat/Hello-World.git", "octocat", "Hello-World"),
        ("https://www.github.com/octocat/repo/tree/main/docs", "octocat", "repo"),
        ("github.com/octocat/repo", "octocat", "repo"),
        ("octocat/repo/", "octocat", "repo"),
    ],
)
def test_parse_accepts_common_forms(raw, owner, name):
    ref = parse_repo_input(raw)
    assert (ref.owner, ref.name) == (owner, name)
    assert ref.full_name == f"{owner}/{name}"


@pytest.mark.parametrize(
    "raw",
    [
        "",
        "   ",
        "just-a-word",
        "a/b/c/d",
        "https://gitlab.com/octocat/repo",
        "https://github.com/octocat",
        "-bad-owner/repo",
        "owner/..",
        "owner/has space",
        "owner/" + "x" * 101,
    ],
)
def test_parse_rejects_invalid_input(raw):
    with pytest.raises(InvalidRepoInput):
        parse_repo_input(raw)


def test_ttl_cache_expires():
    now = [0.0]
    cache = TTLCache(10, clock=lambda: now[0])
    cache.set("k", "v")
    assert cache.get("k") == "v"
    now[0] = 10.0
    assert cache.get("k") is None


def test_sliding_window_limiter_blocks_and_recovers():
    now = [0.0]
    limiter = SlidingWindowLimiter(limit=2, window=60, clock=lambda: now[0])
    assert limiter.hit("ip") is None
    assert limiter.hit("ip") is None
    retry = limiter.hit("ip")
    assert retry is not None and retry > 0
    assert limiter.hit("other") is None  # limits are per key
    now[0] = 61.0
    assert limiter.hit("ip") is None
