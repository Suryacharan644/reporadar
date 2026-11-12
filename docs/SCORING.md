# How the RepoRadar health score works

RepoRadar's score is **transparent and reproducible**. It is the sum of points from
27 checks across 10 categories. The category weights add up to 100.
Every check is evaluated from public GitHub data, and every result in a report shows the
evidence that produced it.

Methodology version: **1.0.0**. The scoring code lives in
[`backend/app/analyzer.py`](../backend/app/analyzer.py); this table is generated from the same
`CHECKS` registry, so the documentation cannot drift from the implementation.

## Rules

1. **Pass** earns the check's full points.
2. **Partial** earns half of the points, rounded down.
3. **Fail** earns zero points.
4. **Severity**: a pass is *good*. A failed check marked *critical* is **Critical**. Any other
   failure or partial result is a **Warning**.
5. **Grades**: A ≥ 90, B ≥ 75, C ≥ 60, D ≥ 40, F < 40.

## Inputs and limits

- The analysis reads the **default branch** file tree (up to GitHub's recursive tree limit), the
  README and CONTRIBUTING file, and the most recent 30 commits, issues, pull requests,
  10 contributors and 5 workflow runs.
- Commit and issue windows are sampled, not full history. Large trees may be truncated; the report
  lists this under *warnings*.
- If a secondary data source fails, that check still runs on the data available and the failure is
  listed under *warnings*. Rate-limit errors are surfaced to the user instead.
- Scores measure what a newcomer can see. They do not judge code quality, security or the
  project's importance.

## Checks

### README quality (15 points)

| Check | Points | Critical if missing | Recommendation when it fails |
| --- | ---: | :---: | --- |
| README exists (`readme.exists`) | 5 | yes | Add a README.md that explains what the project does, who it is for and how to start. |
| README is substantial (`readme.length`) | 4 | no | Expand the README to 800+ characters: purpose, features, install, usage and links. |
| README has install and usage sections (`readme.sections`) | 4 | no | Add 'Installation' and 'Usage' headings so newcomers can get running in minutes. |
| README includes code examples (`readme.code`) | 2 | no | Add a fenced code block showing the most common command or API call. |

### Documentation (8 points)

| Check | Points | Critical if missing | Recommendation when it fails |
| --- | ---: | :---: | --- |
| Dedicated documentation (`docs.folder`) | 4 | no | Create a docs/ folder for guides, architecture notes and API reference. |
| Repository description set (`docs.description`) | 2 | no | Set a one-sentence description in the repository settings. |
| Topics set (`docs.topics`) | 2 | no | Add 3-6 topics in the repository settings so people can find the project. |

### License (10 points)

| Check | Points | Critical if missing | Recommendation when it fails |
| --- | ---: | :---: | --- |
| LICENSE file present (`license.file`) | 7 | yes | Add a LICENSE file (MIT, Apache-2.0 or GPL-3.0 are common choices for open source). |
| License type recognised (`license.spdx`) | 3 | no | Use a standard, SPDX-recognised license text so GitHub and tools can detect it. |

### CONTRIBUTING guide (10 points)

| Check | Points | Critical if missing | Recommendation when it fails |
| --- | ---: | :---: | --- |
| CONTRIBUTING.md present (`contributing.file`) | 6 | no | Add CONTRIBUTING.md explaining how to set up, test and submit changes. |
| CONTRIBUTING covers setup, tests, PRs and style (`contributing.content`) | 4 | no | Cover setup, running tests, the pull request process and code style or commit conventions. |

### Issue templates (7 points)

| Check | Points | Critical if missing | Recommendation when it fails |
| --- | ---: | :---: | --- |
| Issue templates exist (`issues.templates`) | 4 | no | Add .github/ISSUE_TEMPLATE/ templates so bug reports arrive with the details you need. |
| Bug and feature templates (`issues.templates_variety`) | 3 | no | Provide separate bug report and feature request templates. |

### Pull request template (5 points)

| Check | Points | Critical if missing | Recommendation when it fails |
| --- | ---: | :---: | --- |
| Pull request template (`pr.template`) | 5 | no | Add .github/PULL_REQUEST_TEMPLATE.md with a checklist for description, tests and linked issues. |

### CI/CD (12 points)

| Check | Points | Critical if missing | Recommendation when it fails |
| --- | ---: | :---: | --- |
| CI workflows configured (`ci.workflows`) | 6 | yes | Add a GitHub Actions workflow that runs tests on every push and pull request. |
| Recent CI runs succeed (`ci.runs`) | 4 | no | Investigate failing workflow runs; a green main branch builds trust. |
| Dependency or security automation (`ci.automation`) | 2 | no | Enable Dependabot or Renovate, and consider CodeQL scanning. |

### Automated tests (12 points)

| Check | Points | Critical if missing | Recommendation when it fails |
| --- | ---: | :---: | --- |
| Test files exist (`tests.files`) | 6 | yes | Add automated tests for core behaviour and wire them into CI. |
| Meaningful test suite (`tests.volume`) | 3 | no | Grow the suite to cover edge cases and each public entry point. |
| Test runner configured (`tests.config`) | 3 | no | Add a test configuration (pytest.ini, jest.config.*, vitest.config.*) so tests run the same everywhere. |

### Dependencies (8 points)

| Check | Points | Critical if missing | Recommendation when it fails |
| --- | ---: | :---: | --- |
| Dependency manifest (`deps.manifest`) | 3 | no | Declare dependencies in a manifest file so installs are predictable. |
| Lockfile committed (`deps.lockfile`) | 3 | no | Commit a lockfile so every contributor and CI run installs identical versions. |
| Dependency update bot (`deps.automation`) | 2 | no | Enable Dependabot or Renovate to receive security and version updates automatically. |

### Repository activity (13 points)

| Check | Points | Critical if missing | Recommendation when it fails |
| --- | ---: | :---: | --- |
| Recently pushed (`activity.recency`) | 5 | yes | Push maintenance changes or archive the repository to signal its status honestly. |
| Commit activity (90 days) (`activity.commits`) | 4 | no | Maintain a steady cadence of commits, even small fixes, so contributors see momentum. |
| Issues get closed (`activity.responsiveness`) | 2 | no | Triage issues regularly: label them, reply, and close what is resolved or out of scope. |
| Pull requests get merged (`activity.prs`) | 2 | no | Review and merge contributions promptly, or explain why they are declined. |


## Changing the rules

Scoring changes must update `CHECKS` / `CATEGORIES` in `backend/app/analyzer.py`, bump
`METHODOLOGY_VERSION` when results change, regenerate this file, and include unit tests in
`backend/tests/unit/test_scoring.py`. The module asserts at import time that weights total 100.
