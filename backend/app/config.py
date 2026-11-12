"""Runtime configuration, read from environment variables.

Secrets (GITHUB_TOKEN, SUPABASE_SERVICE_KEY) are only ever read here, on the
server. They are never sent to the frontend.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass


def _int(env: Mapping[str, str], name: str, default: int) -> int:
    raw = env.get(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return int(raw)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer, got {raw!r}") from exc


@dataclass(frozen=True)
class Settings:
    github_token: str | None = None
    supabase_url: str | None = None
    supabase_service_key: str | None = None
    cache_ttl_seconds: int = 900
    rate_limit_per_minute: int = 20
    trust_proxy: bool = False
    allowed_origins: tuple[str, ...] = ("http://localhost:3000",)

    @property
    def persistence_enabled(self) -> bool:
        return bool(self.supabase_url and self.supabase_service_key)

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> "Settings":
        env = os.environ if env is None else env
        origins = env.get("ALLOWED_ORIGINS", "http://localhost:3000")
        return cls(
            github_token=(env.get("GITHUB_TOKEN") or None),
            supabase_url=(env.get("SUPABASE_URL") or None),
            supabase_service_key=(env.get("SUPABASE_SERVICE_KEY") or None),
            cache_ttl_seconds=_int(env, "CACHE_TTL_SECONDS", 900),
            rate_limit_per_minute=_int(env, "RATE_LIMIT_PER_MINUTE", 20),
            trust_proxy=env.get("TRUST_PROXY", "0") in ("1", "true", "yes"),
            allowed_origins=tuple(o.strip() for o in origins.split(",") if o.strip()),
        )
