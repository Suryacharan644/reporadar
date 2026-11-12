# Architecture

## Components

1. **Next.js web app** (`frontend/`): App Router pages, Tailwind CSS dark UI, client components
   that call the API. It never talks to GitHub or Supabase directly.
2. **API proxy** (`frontend/app/api/[...path]/route.ts`): forwards `/api/*` to the backend on the
   server. Only allows safe path segments and bounded request bodies.
3. **FastAPI backend** (`backend/app/`): the only component with GitHub credentials. It exposes the
   JSON API, caches analyses, rate-limits callers, and persists shared reports.
4. **GitHub Action** (`action/`, `backend/app/action_runner.py`): reuses the same collector and
   analyzer, writes Markdown and JSON, and maintains one PR comment.

## Analysis pipeline

```
owner/repo ─► parse_repo_input ─► GitHubClient ─► collect_snapshot ─► RepoSnapshot
                                                                       │
                                  ┌────────────────────────────────────┤
                                  ▼                                    ▼
                           evaluate (pure)                      generators (pure)
                                  │
                                  ▼
                           build_report ─► TTL cache ─► API / Action / share store
```

- **`collect_snapshot`** makes the required calls (repository, file tree, README) and several
  optional calls in parallel (commits, issues, PRs, contributors, workflow runs, CONTRIBUTING).
  Optional failures become *warnings*. Rate-limit errors always propagate.
- **`RepoSnapshot`** is plain data. Scoring never performs I/O, which makes every rule testable
  with synthetic snapshots.
- **`evaluate`** applies each `CheckSpec` and computes points, severity and recommendations.

## GitHub API usage

| Endpoint | Used for | Calls per analysis |
| --- | --- | --- |
| `GET /repos/{o}/{r}` | metadata, privacy check | 1 |
| `GET /repos/{o}/{r}/git/trees/{branch}?recursive=1` | file inventory | 1 |
| `GET /repos/{o}/{r}/readme` | README analysis | 1 |
| `GET /repos/{o}/{r}/contents/CONTRIBUTING.md` | CONTRIBUTING analysis | 0–1 |
| `commits`, `issues`, `pulls`, `contributors`, `actions/runs` | activity | 5 |
| `GET /search/issues` | contribution finder | 1 per page |

Roughly eight requests are made per uncached analysis. The TTL cache (default 15 minutes) and the
per-IP limiter keep usage well inside GitHub's limits. The search API has its own, lower limit.

## Privacy and security

- Only public repositories are analysed. A repository reported as private is refused and never
  stored.
- Secrets (`GITHUB_TOKEN`, `SUPABASE_SERVICE_KEY`) are read only by the backend. The Next.js
  bundle contains only `NEXT_PUBLIC_*`-style values, and none are needed.
- Shared reports contain only the analysis document. Supabase row-level security is enabled with
  no public policies.
- Security headers (CSP, frame and content-type protections) are set in `frontend/next.config.mjs`.
- Contribution search results come from public issues. Configure `GITHUB_TOKEN` as a fine-grained
  token with no repositories selected, so it can only read public data. Search results are not
  re-checked for visibility, so this token scope is what keeps private issues out.

## Failure modes

| Situation | Behaviour |
| --- | --- |
| Repository not found or private | `404` with a clear message |
| GitHub rate limit | `429` with `Retry-After`; UI shows a countdown |
| GitHub unavailable | `502`; the UI offers retry |
| Backend unreachable from the proxy | `503` |
| Secondary data missing | Report still returned, with `warnings` listed |
| Empty repository | Commits and tree warnings; checks fail with evidence |

## Persistence

`ReportStore` has two implementations: `MemoryStore` (default, for development) and `SupabaseStore`
(PostgREST, used when `SUPABASE_URL` and `SUPABASE_SERVICE_KEY` are set). Schema:
[`supabase/schema.sql`](../supabase/schema.sql).

## Known limits

- Analysis uses the default branch and recent samples, not full history.
- The in-process cache and rate limiter are per backend process. Run one process, or move them to
  a shared store (for example Redis) when scaling out horizontally.
- Scores are heuristics about contributor experience, not a measure of code quality.
