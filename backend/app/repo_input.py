"""Parse and validate user-supplied repository references.

Accepts ``owner/repo``, ``github.com/owner/repo`` and full ``https://github.com/...``
URLs (with optional ``.git`` suffix or extra path segments such as ``/tree/main``).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import urlparse

OWNER_RE = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})$")
REPO_RE = re.compile(r"^[A-Za-z0-9._-]{1,100}$")
_SCHEME_RE = re.compile(r"^[a-z][a-z0-9+.-]*://", re.IGNORECASE)


class InvalidRepoInput(ValueError):
    """Raised when user input cannot be turned into a GitHub repository reference."""


@dataclass(frozen=True)
class RepoRef:
    owner: str
    name: str

    @property
    def full_name(self) -> str:
        return f"{self.owner}/{self.name}"


def _validate(owner: str, name: str) -> RepoRef:
    if not OWNER_RE.match(owner):
        raise InvalidRepoInput(f"'{owner}' is not a valid GitHub owner name.")
    if name.endswith(".git"):
        name = name[: -len(".git")]
    if name in (".", "..") or not REPO_RE.match(name):
        raise InvalidRepoInput(f"'{name}' is not a valid GitHub repository name.")
    return RepoRef(owner=owner, name=name)


def parse_repo_input(raw: str | None) -> RepoRef:
    text = (raw or "").strip()
    if not text:
        raise InvalidRepoInput("Enter a GitHub repository URL or owner/repo.")

    lowered = text.lower()
    if _SCHEME_RE.match(text) or lowered.startswith(("github.com/", "www.github.com/")):
        if not _SCHEME_RE.match(text):
            text = "https://" + text
        parsed = urlparse(text)
        if (parsed.hostname or "") not in ("github.com", "www.github.com"):
            raise InvalidRepoInput("Only github.com repositories are supported.")
        parts = [p for p in parsed.path.split("/") if p]
        if len(parts) < 2:
            raise InvalidRepoInput("The URL must point to a repository, e.g. github.com/owner/repo.")
        return _validate(parts[0], parts[1])

    parts = text.strip("/").split("/")
    if len(parts) != 2:
        raise InvalidRepoInput("Use the format owner/repo or a github.com repository URL.")
    return _validate(parts[0], parts[1])
