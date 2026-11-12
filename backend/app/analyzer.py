"""Repository health analysis.

This module is pure: it turns a ``RepoSnapshot`` (plain data collected from the
GitHub API) into checks, a score and a report. No network calls happen here,
which keeps every rule unit-testable with synthetic snapshots.

Scoring model
-------------
* Ten categories whose weights sum to 100.
* Each category is made of one or more checks with a fixed point value.
* A check is ``pass`` (full points), ``partial`` (half points, rounded down)
  or ``fail`` (zero points). Every result carries the evidence that produced it.
* Severity: ``good`` for passes; ``critical`` for failed checks flagged as
  critical; ``warning`` for every other failure or partial result.

The full rule table is documented in ``docs/SCORING.md`` and must be kept in
sync with ``CHECKS`` below (a unit test enforces the weight total).
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Literal

PASS, PARTIAL, FAIL = "pass", "partial", "fail"
Status = Literal["pass", "partial", "fail"]
Severity = Literal["critical", "warning", "good"]

METHODOLOGY_VERSION = "1.0.0"

# --------------------------------------------------------------------- snapshot


@dataclass
class CommitInfo:
    sha: str
    message: str
    author: str
    date: datetime
    url: str | None = None


@dataclass
class IssueInfo:
    number: int
    title: str
    state: str
    created_at: datetime
    closed_at: datetime | None
    url: str | None
    comments: int = 0


@dataclass
class PullInfo:
    number: int
    title: str
    state: str
    created_at: datetime
    merged_at: datetime | None
    url: str | None


@dataclass
class ContributorInfo:
    login: str
    contributions: int
    url: str | None
    avatar_url: str | None


@dataclass
class RunInfo:
    name: str
    status: str
    conclusion: str | None
    created_at: datetime
    url: str | None


@dataclass
class RepoSnapshot:
    owner: str
    name: str
    html_url: str
    fetched_at: datetime
    description: str | None = None
    topics: list[str] = field(default_factory=list)
    homepage: str | None = None
    license_spdx: str | None = None
    stars: int = 0
    forks: int = 0
    open_issues: int = 0
    language: str | None = None
    default_branch: str = "main"
    pushed_at: datetime | None = None
    created_at: datetime | None = None
    archived: bool = False
    private: bool = False
    paths: list[str] = field(default_factory=list)
    tree_truncated: bool = False
    readme: str | None = None
    contributing: str | None = None
    commits: list[CommitInfo] = field(default_factory=list)
    issues: list[IssueInfo] = field(default_factory=list)
    pulls: list[PullInfo] = field(default_factory=list)
    contributors: list[ContributorInfo] = field(default_factory=list)
    runs: list[RunInfo] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def full_name(self) -> str:
        return f"{self.owner}/{self.name}"


# ------------------------------------------------------------------ path helpers

MANIFEST_NAMES = {
    "package.json", "requirements.txt", "pyproject.toml", "pipfile", "setup.py", "setup.cfg",
    "go.mod", "cargo.toml", "gemfile", "pom.xml", "build.gradle", "build.gradle.kts",
    "composer.json", "mix.exs", "pubspec.yaml",
}
LOCKFILE_NAMES = {
    "package-lock.json", "yarn.lock", "pnpm-lock.yaml", "bun.lockb", "bun.lock", "poetry.lock",
    "uv.lock", "pipfile.lock", "cargo.lock", "go.sum", "gemfile.lock", "composer.lock", "pubspec.lock",
}
TEST_CONFIG_NAMES = {
    "pytest.ini", "tox.ini", "jest.config.js", "jest.config.ts", "jest.config.cjs", "jest.config.mjs",
    "vitest.config.ts", "vitest.config.js", "vitest.config.mts", ".mocharc.js", ".mocharc.json",
    ".mocharc.yml", "karma.conf.js",
}
TEST_PATH_RE = re.compile(
    r"(^|/)(tests?|__tests__|spec)/"
    r"|(^|/)test_[^/]*\.py$"
    r"|_test\.(py|go)$"
    r"|\.(test|spec)\.(js|jsx|ts|tsx|mjs|cjs)$"
    r"|(^|/)[^/]*Test\.java$"
    r"|_spec\.rb$",
    re.IGNORECASE,
)
DOC_DIRS = ("docs/", "documentation/", "doc/", "wiki/")
DEPENDABOT_OR_RENOVATE = {"dependabot.yml", "dependabot.yaml", "renovate.json", ".renovaterc", ".renovaterc.json"}


def _lower(paths: list[str]) -> list[str]:
    return [p.lower() for p in paths]


def _basename(path: str) -> str:
    return path.rsplit("/", 1)[-1].lower()


def _workflow_files(s: RepoSnapshot) -> list[str]:
    return [p for p in _lower(s.paths) if p.startswith(".github/workflows/") and p.endswith((".yml", ".yaml"))]


def _issue_template_files(s: RepoSnapshot) -> list[str]:
    return [
        p
        for p in _lower(s.paths)
        if p.startswith(".github/issue_template/") or p == ".github/issue_template.md"
    ]


def _has_dependabot_or_renovate(s: RepoSnapshot) -> bool:
    return any(_basename(p) in DEPENDABOT_OR_RENOVATE for p in s.paths)


def _root_license(s: RepoSnapshot) -> bool:
    return any(re.fullmatch(r"(license|licence|copying)(\.(md|txt|rst))?", p.lower()) for p in s.paths if "/" not in p)


# ------------------------------------------------------------------ check rules
# Each rule returns (status, evidence). Keep evidence specific: it is shown to users.


def check_readme_exists(s: RepoSnapshot) -> tuple[Status, str]:
    if s.readme and s.readme.strip():
        return PASS, f"README found ({len(s.readme.strip())} characters)."
    return FAIL, "No README was found at the repository root."


def check_readme_length(s: RepoSnapshot) -> tuple[Status, str]:
    n = len((s.readme or "").strip())
    if n >= 800:
        return PASS, f"README is {n} characters long."
    if n >= 300:
        return PARTIAL, f"README is {n} characters; 800+ usually covers purpose, install and usage."
    return FAIL, "README is missing or under 300 characters."


def check_readme_sections(s: RepoSnapshot) -> tuple[Status, str]:
    headings = [h.lower() for h in re.findall(r"^#{1,6}\s+(.+)$", s.readme or "", re.MULTILINE)]
    has_install = any(re.search(r"install|getting started|quick ?start|setup", h) for h in headings)
    has_usage = any(re.search(r"usage|example|how to|running|api", h) for h in headings)
    if has_install and has_usage:
        return PASS, "README has install/setup and usage/example sections."
    if has_install or has_usage:
        missing = "usage/example" if has_install else "install/setup"
        return PARTIAL, f"README has no {missing} section heading."
    return FAIL, "README has no install/setup or usage headings."


def check_readme_code(s: RepoSnapshot) -> tuple[Status, str]:
    if (s.readme or "").count("```") >= 2:
        return PASS, "README includes fenced code examples."
    return FAIL, "README has no fenced code examples."


def check_docs_folder(s: RepoSnapshot) -> tuple[Status, str]:
    for p in _lower(s.paths):
        if p.startswith(DOC_DIRS):
            return PASS, f"Documentation folder found ({p.split('/', 1)[0]}/)."
    return FAIL, "No docs/, documentation/ or wiki/ folder found."


def check_description(s: RepoSnapshot) -> tuple[Status, str]:
    if s.description and len(s.description.strip()) >= 10:
        return PASS, "Repository has a description."
    return FAIL, "Repository description is empty or very short."


def check_topics(s: RepoSnapshot) -> tuple[Status, str]:
    if s.topics:
        return PASS, f"{len(s.topics)} topic(s) set, helping developers discover the project."
    if s.homepage:
        return PARTIAL, "A homepage is set but no topics; add topics for discoverability."
    return FAIL, "No topics or homepage set."


def check_license_file(s: RepoSnapshot) -> tuple[Status, str]:
    if _root_license(s):
        return PASS, "LICENSE file found at the repository root."
    return FAIL, "No LICENSE file at the repository root. Without one, the code is not open source."


def check_license_spdx(s: RepoSnapshot) -> tuple[Status, str]:
    if s.license_spdx and s.license_spdx != "NOASSERTION":
        return PASS, f"GitHub identifies the license as {s.license_spdx}."
    if _root_license(s):
        return PARTIAL, "A license file exists but GitHub could not identify its type."
    return FAIL, "No recognised license."


CONTRIBUTING_PATHS = {"contributing.md", ".github/contributing.md", "docs/contributing.md"}


def check_contributing_file(s: RepoSnapshot) -> tuple[Status, str]:
    for p in _lower(s.paths):
        if p in CONTRIBUTING_PATHS:
            return PASS, f"{p} found."
    return FAIL, "No CONTRIBUTING.md at the root, .github/ or docs/."


CONTRIBUTING_GROUPS = {
    "setup": r"install|setup|develop|environment|getting started",
    "testing": r"test",
    "pull requests": r"pull request|\bpr\b",
    "style or commits": r"style|lint|format|commit",
}


def check_contributing_content(s: RepoSnapshot) -> tuple[Status, str]:
    if not s.contributing:
        return FAIL, "No CONTRIBUTING file to inspect."
    text = s.contributing.lower()
    covered = [name for name, pattern in CONTRIBUTING_GROUPS.items() if re.search(pattern, text)]
    evidence = f"Covers: {', '.join(covered) if covered else 'none of the expected topics'}."
    if len(covered) >= 3:
        return PASS, evidence
    if len(covered) == 2:
        return PARTIAL, evidence
    return FAIL, evidence


def check_issue_templates_exist(s: RepoSnapshot) -> tuple[Status, str]:
    n = len(_issue_template_files(s))
    if n:
        return PASS, f"{n} issue template file(s) found."
    return FAIL, "No issue templates in .github/ISSUE_TEMPLATE/."


def check_issue_templates_variety(s: RepoSnapshot) -> tuple[Status, str]:
    n = len([p for p in _issue_template_files(s) if _basename(p) != "config.yml"])
    if n >= 2:
        return PASS, f"{n} templates (for example bug report and feature request)."
    if n == 1:
        return PARTIAL, "Only one issue template; add separate bug and feature templates."
    return FAIL, "No issue templates to evaluate."


def check_pr_template(s: RepoSnapshot) -> tuple[Status, str]:
    for p in _lower(s.paths):
        if p in {".github/pull_request_template.md", "pull_request_template.md", "docs/pull_request_template.md"}:
            return PASS, f"{p} found."
        if p.startswith(".github/pull_request_template/"):
            return PASS, "Pull request template folder found."
    return FAIL, "No pull request template found."


def check_ci_workflows(s: RepoSnapshot) -> tuple[Status, str]:
    n = len(_workflow_files(s))
    if n:
        return PASS, f"{n} GitHub Actions workflow(s) configured."
    return FAIL, "No workflows in .github/workflows/."


def check_ci_runs(s: RepoSnapshot) -> tuple[Status, str]:
    if s.runs:
        successes = [r for r in s.runs if r.conclusion == "success"]
        if successes:
            return PASS, f"{len(successes)} of the last {len(s.runs)} workflow runs succeeded."
        latest = s.runs[0].conclusion or s.runs[0].status
        return PARTIAL, f"Recent workflow runs exist but none succeeded (latest: {latest})."
    if _workflow_files(s):
        return PARTIAL, "Workflows exist but no recent runs were returned."
    return FAIL, "No workflow runs found."


def check_ci_automation(s: RepoSnapshot) -> tuple[Status, str]:
    if _has_dependabot_or_renovate(s):
        return PASS, "Automated dependency updates configured (Dependabot or Renovate)."
    if any("codeql" in p or "security" in p for p in _lower(_workflow_files(s))):
        return PASS, "Security scanning workflow found."
    return FAIL, "No Dependabot, Renovate or security scanning configured."


def check_test_files(s: RepoSnapshot) -> tuple[Status, str]:
    n = len([p for p in s.paths if TEST_PATH_RE.search(p)])
    if n:
        return PASS, f"{n} test file(s) found."
    return FAIL, "No test files found (test/, tests/, __tests__/, *.test.*, test_*.py ...)."


def check_test_volume(s: RepoSnapshot) -> tuple[Status, str]:
    n = len([p for p in s.paths if TEST_PATH_RE.search(p)])
    if n >= 5:
        return PASS, f"{n} test files suggest a meaningful suite."
    if n >= 1:
        return PARTIAL, f"Only {n} test file(s); broaden coverage."
    return FAIL, "No test files to evaluate."


def check_test_config(s: RepoSnapshot) -> tuple[Status, str]:
    found = [p for p in s.paths if _basename(p) in TEST_CONFIG_NAMES]
    if found:
        return PASS, f"Test runner configuration found ({_basename(found[0])})."
    return FAIL, "No test runner configuration found."


def check_dependency_manifest(s: RepoSnapshot) -> tuple[Status, str]:
    found = [p for p in s.paths if _basename(p) in MANIFEST_NAMES]
    if found:
        return PASS, f"Dependency manifest found ({found[0]})."
    return FAIL, "No dependency manifest (package.json, requirements.txt, pyproject.toml ...)."


def check_dependency_lockfile(s: RepoSnapshot) -> tuple[Status, str]:
    found = [p for p in s.paths if _basename(p) in LOCKFILE_NAMES]
    if found:
        return PASS, f"Lockfile found ({found[0]}); builds are reproducible."
    return FAIL, "No lockfile found; builds may not be reproducible."


def check_dependency_automation(s: RepoSnapshot) -> tuple[Status, str]:
    if _has_dependabot_or_renovate(s):
        return PASS, "Dependency update bot configured."
    return FAIL, "No Dependabot or Renovate configuration."


def check_recency(s: RepoSnapshot) -> tuple[Status, str]:
    if s.pushed_at is None:
        return FAIL, "Last push date unavailable."
    days = (s.fetched_at - s.pushed_at).days
    if days <= 30:
        return PASS, f"Last push {days} day(s) ago."
    if days <= 180:
        return PARTIAL, f"Last push {days} days ago."
    return FAIL, f"Last push {days} days ago; the project looks stale."


def check_commit_activity(s: RepoSnapshot) -> tuple[Status, str]:
    since = s.fetched_at - timedelta(days=90)
    n = len([c for c in s.commits if c.date >= since])
    if n >= 10:
        return PASS, f"{n} commit(s) in the last 90 days."
    if n >= 1:
        return PARTIAL, f"Only {n} commit(s) in the last 90 days."
    return FAIL, "No commits in the last 90 days."


def check_issue_responsiveness(s: RepoSnapshot) -> tuple[Status, str]:
    if not s.issues:
        return PARTIAL, "No issues to evaluate yet."
    closed = len([i for i in s.issues if i.state == "closed"])
    ratio = closed / len(s.issues)
    evidence = f"{closed} of the {len(s.issues)} most recent issues are closed."
    if ratio >= 0.5:
        return PASS, evidence
    if closed > 0:
        return PARTIAL, evidence
    return FAIL, evidence


def check_pr_merges(s: RepoSnapshot) -> tuple[Status, str]:
    if not s.pulls:
        return FAIL, "No pull requests found."
    merged = len([p for p in s.pulls if p.merged_at])
    if merged:
        return PASS, f"{merged} of the {len(s.pulls)} most recent pull requests were merged."
    return PARTIAL, "Pull requests exist but none have been merged recently."


# ------------------------------------------------------------- check registry


@dataclass(frozen=True)
class CheckSpec:
    id: str
    category: str
    title: str
    max_points: int
    critical: bool
    rule: Callable[[RepoSnapshot], tuple[Status, str]]
    recommendation: str


CATEGORIES: list[tuple[str, str, int]] = [
    ("readme", "README quality", 15),
    ("documentation", "Documentation", 8),
    ("license", "License", 10),
    ("contributing", "CONTRIBUTING guide", 10),
    ("issue_templates", "Issue templates", 7),
    ("pr_template", "Pull request template", 5),
    ("ci", "CI/CD", 12),
    ("tests", "Automated tests", 12),
    ("dependencies", "Dependencies", 8),
    ("activity", "Repository activity", 13),
]

CHECKS: list[CheckSpec] = [
    CheckSpec("readme.exists", "readme", "README exists", 5, True, check_readme_exists,
              "Add a README.md that explains what the project does, who it is for and how to start."),
    CheckSpec("readme.length", "readme", "README is substantial", 4, False, check_readme_length,
              "Expand the README to 800+ characters: purpose, features, install, usage and links."),
    CheckSpec("readme.sections", "readme", "README has install and usage sections", 4, False, check_readme_sections,
              "Add 'Installation' and 'Usage' headings so newcomers can get running in minutes."),
    CheckSpec("readme.code", "readme", "README includes code examples", 2, False, check_readme_code,
              "Add a fenced code block showing the most common command or API call."),
    CheckSpec("docs.folder", "documentation", "Dedicated documentation", 4, False, check_docs_folder,
              "Create a docs/ folder for guides, architecture notes and API reference."),
    CheckSpec("docs.description", "documentation", "Repository description set", 2, False, check_description,
              "Set a one-sentence description in the repository settings."),
    CheckSpec("docs.topics", "documentation", "Topics set", 2, False, check_topics,
              "Add 3-6 topics in the repository settings so people can find the project."),
    CheckSpec("license.file", "license", "LICENSE file present", 7, True, check_license_file,
              "Add a LICENSE file (MIT, Apache-2.0 or GPL-3.0 are common choices for open source)."),
    CheckSpec("license.spdx", "license", "License type recognised", 3, False, check_license_spdx,
              "Use a standard, SPDX-recognised license text so GitHub and tools can detect it."),
    CheckSpec("contributing.file", "contributing", "CONTRIBUTING.md present", 6, False, check_contributing_file,
              "Add CONTRIBUTING.md explaining how to set up, test and submit changes."),
    CheckSpec("contributing.content", "contributing", "CONTRIBUTING covers setup, tests, PRs and style", 4, False,
              check_contributing_content,
              "Cover setup, running tests, the pull request process and code style or commit conventions."),
    CheckSpec("issues.templates", "issue_templates", "Issue templates exist", 4, False, check_issue_templates_exist,
              "Add .github/ISSUE_TEMPLATE/ templates so bug reports arrive with the details you need."),
    CheckSpec("issues.templates_variety", "issue_templates", "Bug and feature templates", 3, False,
              check_issue_templates_variety,
              "Provide separate bug report and feature request templates."),
    CheckSpec("pr.template", "pr_template", "Pull request template", 5, False, check_pr_template,
              "Add .github/PULL_REQUEST_TEMPLATE.md with a checklist for description, tests and linked issues."),
    CheckSpec("ci.workflows", "ci", "CI workflows configured", 6, True, check_ci_workflows,
              "Add a GitHub Actions workflow that runs tests on every push and pull request."),
    CheckSpec("ci.runs", "ci", "Recent CI runs succeed", 4, False, check_ci_runs,
              "Investigate failing workflow runs; a green main branch builds trust."),
    CheckSpec("ci.automation", "ci", "Dependency or security automation", 2, False, check_ci_automation,
              "Enable Dependabot or Renovate, and consider CodeQL scanning."),
    CheckSpec("tests.files", "tests", "Test files exist", 6, True, check_test_files,
              "Add automated tests for core behaviour and wire them into CI."),
    CheckSpec("tests.volume", "tests", "Meaningful test suite", 3, False, check_test_volume,
              "Grow the suite to cover edge cases and each public entry point."),
    CheckSpec("tests.config", "tests", "Test runner configured", 3, False, check_test_config,
              "Add a test configuration (pytest.ini, jest.config.*, vitest.config.*) so tests run the same everywhere."),
    CheckSpec("deps.manifest", "dependencies", "Dependency manifest", 3, False, check_dependency_manifest,
              "Declare dependencies in a manifest file so installs are predictable."),
    CheckSpec("deps.lockfile", "dependencies", "Lockfile committed", 3, False, check_dependency_lockfile,
              "Commit a lockfile so every contributor and CI run installs identical versions."),
    CheckSpec("deps.automation", "dependencies", "Dependency update bot", 2, False, check_dependency_automation,
              "Enable Dependabot or Renovate to receive security and version updates automatically."),
    CheckSpec("activity.recency", "activity", "Recently pushed", 5, True, check_recency,
              "Push maintenance changes or archive the repository to signal its status honestly."),
    CheckSpec("activity.commits", "activity", "Commit activity (90 days)", 4, False, check_commit_activity,
              "Maintain a steady cadence of commits, even small fixes, so contributors see momentum."),
    CheckSpec("activity.responsiveness", "activity", "Issues get closed", 2, False, check_issue_responsiveness,
              "Triage issues regularly: label them, reply, and close what is resolved or out of scope."),
    CheckSpec("activity.prs", "activity", "Pull requests get merged", 2, False, check_pr_merges,
              "Review and merge contributions promptly, or explain why they are declined."),
]

_total_weight = sum(weight for _, _, weight in CATEGORIES)
assert _total_weight == 100, f"Category weights must total 100, got {_total_weight}"
for _cid, _, _ in CATEGORIES:
    _cat_points = sum(c.max_points for c in CHECKS if c.category == _cid)
    _cat_weight = next(w for cid, _, w in CATEGORIES if cid == _cid)
    assert _cat_points == _cat_weight, f"Checks for {_cid} total {_cat_points}, expected {_cat_weight}"


# ----------------------------------------------------------------- evaluation


@dataclass
class CheckResult:
    id: str
    category: str
    title: str
    status: str
    severity: str
    points: int
    max_points: int
    evidence: str
    recommendation: str


@dataclass
class CategoryResult:
    id: str
    title: str
    weight: int
    points: int
    max_points: int


@dataclass
class Evaluation:
    score: int
    grade: str
    verdict: str
    checks: list[CheckResult]
    categories: list[CategoryResult]
    summary: dict[str, int]


def points_for(status: str, max_points: int) -> int:
    if status == PASS:
        return max_points
    if status == PARTIAL:
        return max_points // 2
    return 0


def grade_for(score: int) -> str:
    if score >= 90:
        return "A"
    if score >= 75:
        return "B"
    if score >= 60:
        return "C"
    if score >= 40:
        return "D"
    return "F"


def verdict_for(score: int) -> str:
    if score >= 85:
        return "Contributor-ready: newcomers can find, set up and contribute with confidence."
    if score >= 70:
        return "Healthy: a few gaps could stop some contributors."
    if score >= 50:
        return "Needs work: contributors will likely hit friction early on."
    return "At risk: most contributors will leave before their first contribution."


def evaluate(snapshot: RepoSnapshot) -> Evaluation:
    checks: list[CheckResult] = []
    for spec in CHECKS:
        status, evidence = spec.rule(snapshot)
        if status == PASS:
            severity = "good"
        elif status == FAIL and spec.critical:
            severity = "critical"
        else:
            severity = "warning"
        checks.append(
            CheckResult(
                id=spec.id,
                category=spec.category,
                title=spec.title,
                status=status,
                severity=severity,
                points=points_for(status, spec.max_points),
                max_points=spec.max_points,
                evidence=evidence,
                recommendation="" if status == PASS else spec.recommendation,
            )
        )

    categories: list[CategoryResult] = []
    for cid, title, weight in CATEGORIES:
        cat_checks = [c for c in checks if c.category == cid]
        categories.append(
            CategoryResult(
                id=cid,
                title=title,
                weight=weight,
                points=sum(c.points for c in cat_checks),
                max_points=sum(c.max_points for c in cat_checks),
            )
        )

    score = sum(c.points for c in checks)
    summary = {
        "critical": sum(1 for c in checks if c.severity == "critical"),
        "warning": sum(1 for c in checks if c.severity == "warning"),
        "good": sum(1 for c in checks if c.severity == "good"),
    }
    return Evaluation(
        score=score,
        grade=grade_for(score),
        verdict=verdict_for(score),
        checks=checks,
        categories=categories,
        summary=summary,
    )


def build_timestamp() -> datetime:
    return datetime.now(timezone.utc)
