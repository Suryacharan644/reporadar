# RepoRadar

**Find out why developers leave your GitHub repository without contributing.**

RepoRadar analyses any public GitHub repository and produces a transparent 0–100 health score,
ranked findings (Critical, Warning, Good), a concrete fix for every problem, generated starter
files, a shareable report, and a GitHub Action that comments on pull requests.

- **Evidence-based.** Every check shows the evidence it used. The rules are published in
  [docs/SCORING.md](docs/SCORING.md) and generated from the same code that scores repositories.
- **Real data only.** Everything comes from the GitHub REST API at request time.
- **Privacy-aware.** Only public repositories are analysed. The GitHub token and any Supabase
  keys stay on the server.

## Features

| Area | What you get |
| --- | --- |
| Validation | Instant check that the repository exists and is public, as you type |
| Health score | 10 categories, 27 checks, weights summing to 100, grade A–F |
| Findings | Critical, Warning and Good groups, each with evidence and a recommendation |
| Activity | Weekly commit chart, recent commits, issues, PRs, contributors, workflow runs |
| Generators | README.md, CONTRIBUTING.md, issue templates and PR template drafts |
| Sharing | Read-only snapshot links (`/report/<id>`) and an SVG badge endpoint |
| Contribution finder | Open, beginner-labelled issues across GitHub, filterable by label and keyword |
| Automation | Composite GitHub Action: job summary, updated PR comment, optional minimum score |

## Quick start

You need **Node.js 20+** and **Python 3.11+** (3.13 recommended).

```bash
git clone https://github.com/Suryacharan644/reporadar.git
cd reporadar
```

### 1. Start the API

```bash
cd backend
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
export GITHUB_TOKEN=ghp_your_fine_grained_token   # optional, see below
uvicorn app.main:app --reload --port 8000
```

### 2. Start the web app

```bash
cd frontend
npm ci
echo "REPORADAR_API_URL=http://localhost:8000" > .env.local
npm run dev
```

Open http://localhost:3000, paste `owner/repo`, and press **Analyse**.

### GitHub token (strongly recommended)

Unauthenticated GitHub requests are limited to 60 per hour per IP, and one analysis uses about
eight requests. Create a **fine-grained personal access token with no repository access selected**
(which can read public data only) and set `GITHUB_TOKEN`. The limit rises to 5,000 per hour.

## Using the GitHub Action

Add `.github/workflows/repo-health.yml` to any repository:

```yaml
name: RepoRadar health
on:
  pull_request:
  schedule:
    - cron: "0 6 * * 1"

permissions:
  contents: read
  pull-requests: write

jobs:
  health:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: Suryacharan644/reporadar/action@main   # pin a release tag once published
        with:
          min-score: "60"    # fail the job below this score; 0 never fails
```

The action analyses the repository's **default branch**, writes `reporadar-report.md` and
`reporadar-report.json` to the workspace, adds the Markdown to the job summary, and creates or
updates a single comment on the pull request (identified by a hidden marker, so it never spams).
On forked pull requests, where the token is read-only, the comment step logs a warning and the
analysis still runs. See [`.github/workflows/reporadar.yml`](.github/workflows/reporadar.yml) for a
working example.

## API

All endpoints are served by the FastAPI backend and reached through the Next.js `/api` proxy.

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/api/health` | Status and configuration summary (no secrets) |
| GET | `/api/validate?repo=owner/name` | Validate a repository reference and check it is public |
| GET | `/api/repos/{owner}/{name}/report` | Full health report (cached) |
| GET | `/api/repos/{owner}/{name}/generate/{kind}` | `readme`, `contributing`, `issue-templates`, `pr-template` |
| GET | `/api/repos/{owner}/{name}/badge.svg` | Score badge |
| POST | `/api/reports` | Create a shareable snapshot: `{"repo": "owner/name"}` |
| GET | `/api/reports/{id}` | Read a shareable snapshot |
| GET | `/api/contributions?label=&q=&page=` | Beginner-friendly open issues |
| GET | `/api/methodology` | The scoring rules as data |

Errors use `{"error": "message"}`. Rate-limit responses are `429` with a `Retry-After` header.
Interactive OpenAPI docs are at http://localhost:8000/docs.

## Configuration

See [`.env.example`](.env.example) for every variable. The important ones:

| Variable | Where | Purpose |
| --- | --- | --- |
| `GITHUB_TOKEN` | backend | Higher GitHub rate limit. Never sent to the browser. |
| `SUPABASE_URL`, `SUPABASE_SERVICE_KEY` | backend | Persist shared reports. Without them, reports live in memory. |
| `CACHE_TTL_SECONDS` | backend | How long analyses are reused (default 900). |
| `RATE_LIMIT_PER_MINUTE` | backend | Analyses per client IP per minute (default 20). |
| `TRUST_PROXY` | backend | Set to `1` behind a proxy so rate limits see the real client IP. |
| `REPORADAR_API_URL` | frontend | Backend URL used by the Next.js server. |

### Persistence (Supabase, optional)

Apply [`supabase/schema.sql`](supabase/schema.sql) in the Supabase SQL editor. The table has row-level
security enabled with no policies, so only the backend's service-role key can read or write it.

## Architecture

```
Browser ──► Next.js (App Router, Tailwind) ──/api proxy──► FastAPI
                                                          ├─ collector ──► GitHub REST API
                                                          ├─ analyzer  (pure scoring rules)
                                                          ├─ generators / report / badge
                                                          └─ store: memory | Supabase
GitHub Action ──► action_runner ──► same collector + analyzer
```

More detail in [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Testing

```bash
# Backend: unit + integration tests (GitHub is mocked; no network needed)
cd backend && python -m pytest

# Frontend: type checks, unit tests, production build
cd frontend && npm run typecheck && npm test && npm run build
```

The backend suite covers the scoring rules, input parsing, rate limiting, the GitHub client's
error mapping, partial-failure handling, the API surface, persistence, and the Action runner. The
frontend suite covers formatting and validation helpers. CI runs both on every push and pull request.

## Responsible use

- RepoRadar analyses public data only and stores only the report documents you ask it to share.
- Respect GitHub's [Acceptable Use Policies](https://docs.github.com/en/site-policy/acceptable-use-policies/github-acceptable-use-policies).
  Caching and per-IP limits are built in; please do not bypass them.

## Contributing

Contributions are very welcome. Start with [CONTRIBUTING.md](CONTRIBUTING.md) and look for issues
labelled `good first issue`. Report security problems privately as described in [SECURITY.md](SECURITY.md).

## Licence

[MIT](LICENSE)
