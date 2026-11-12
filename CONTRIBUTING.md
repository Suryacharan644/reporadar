# Contributing to RepoRadar

Thank you for helping! RepoRadar is meant to be easy to contribute to, so this guide covers
setup, where things live, and what we expect in a pull request.

## Ground rules

- Be kind and constructive. We follow the [Code of Conduct](CODE_OF_CONDUCT.md).
- Keep changes focused. One logical change per pull request.
- Scoring changes need a rationale, tests, and a methodology version bump (see below).

## Set up

```bash
# Backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Frontend
cd ../frontend
npm ci
```

Run both locally with the instructions in the [README](README.md#quick-start).

## Run the tests

```bash
cd backend && python -m pytest          # unit + integration, no network
cd frontend && npm run typecheck && npm test && npm run build
```

Please add or update tests with every behaviour change. Integration tests use
`backend/tests/helpers.py::fake_github`, an `httpx.MockTransport` that mimics the GitHub endpoints,
so the suite never calls GitHub.

## Where things live

| Area | Path | Notes |
| --- | --- | --- |
| Scoring rules | `backend/app/analyzer.py` | Pure functions; `CHECKS` is the single source of truth |
| GitHub calls | `backend/app/github_client.py`, `backend/app/collector.py` | Rate-limit and privacy handling |
| API routes | `backend/app/main.py` | FastAPI app factory `create_app` |
| Generated files | `backend/app/generators.py` | README, CONTRIBUTING and template drafts |
| Action runner | `backend/app/action_runner.py`, `action/action.yml` | GitHub Action |
| Web UI | `frontend/app`, `frontend/components` | Next.js App Router + Tailwind |
| API proxy | `frontend/app/api/[...path]/route.ts` | The only code that talks to the backend |
| Docs | `docs/` | `SCORING.md` is generated from `CHECKS`; keep them in sync |

## Adding or changing a check

1. Add a pure rule function in `backend/app/analyzer.py` returning `(status, evidence)`.
2. Register a `CheckSpec` in `CHECKS` with its category, max points, criticality and
   recommendation. Points for each category must total its weight; the module asserts this.
3. Add unit tests in `backend/tests/unit/test_checks.py` covering pass, partial and fail.
4. If results change for existing repositories, bump `METHODOLOGY_VERSION`.
5. Regenerate `docs/SCORING.md` so the table matches the code.

## Pull requests

1. Fork, create a branch from `main`, and make your change.
2. Run the test commands above. CI must pass.
3. Open a pull request and fill in the template, including how you tested.
4. Keep the diff small enough to review in one sitting. Split large work into a series of PRs.

## Commit messages

Write short, imperative subjects, for example `Handle empty repository tree`. Explain the *why* in
the body when it is not obvious.

## Reporting bugs and requesting features

Use the issue templates. For security issues, follow [SECURITY.md](SECURITY.md) instead of opening
a public issue.

## Licence

By contributing you agree that your contributions are licensed under the [MIT Licence](LICENSE).
