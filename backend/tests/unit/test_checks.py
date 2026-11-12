from datetime import timedelta

from app.analyzer import FAIL, PARTIAL, PASS, check_commit_activity, check_contributing_content
from app.analyzer import check_issue_responsiveness, check_recency, check_test_files, check_pr_merges
from app.analyzer import check_readme_sections, check_ci_runs, check_license_spdx, IssueInfo
from tests.helpers import NOW, bare_snapshot, healthy_snapshot


def test_readme_sections_need_install_and_usage():
    s = healthy_snapshot(readme="# Title\n\n## Installation\nrun it\n" + "x" * 900)
    assert check_readme_sections(s)[0] == PARTIAL
    s = healthy_snapshot(readme="# Title\n\n## Installation\n\n## Usage\n")
    assert check_readme_sections(s)[0] == PASS
    assert check_readme_sections(bare_snapshot(readme=None))[0] == FAIL


def test_contributing_content_counts_topics():
    full = healthy_snapshot(contributing="setup install\ntest suite\npull request flow\nlint and style")
    assert check_contributing_content(full)[0] == PASS
    two = healthy_snapshot(contributing="install then test")
    assert check_contributing_content(two)[0] == PARTIAL
    assert check_contributing_content(healthy_snapshot(contributing=None))[0] == FAIL


def test_recency_thresholds():
    assert check_recency(healthy_snapshot(pushed_at=NOW - timedelta(days=10)))[0] == PASS
    assert check_recency(healthy_snapshot(pushed_at=NOW - timedelta(days=100)))[0] == PARTIAL
    assert check_recency(healthy_snapshot(pushed_at=NOW - timedelta(days=400)))[0] == FAIL
    assert check_recency(healthy_snapshot(pushed_at=None))[0] == FAIL


def test_commit_activity_window_is_90_days():
    recent = [c for c in healthy_snapshot().commits]
    assert check_commit_activity(healthy_snapshot(commits=recent))[0] == PASS
    old_only = [type(c)(**{**c.__dict__, "date": NOW - timedelta(days=200)}) for c in recent]
    assert check_commit_activity(healthy_snapshot(commits=old_only))[0] == FAIL


def test_issue_responsiveness_ratio():
    issues = [
        IssueInfo(i, "t", "closed" if i < 3 else "open", NOW, None, None) for i in range(5)
    ]
    status, evidence = check_issue_responsiveness(healthy_snapshot(issues=issues))
    assert status == PASS  # 3 of 5 closed is 60%, which meets the 50% bar
    assert "3 of the 5" in evidence


def test_issue_responsiveness_partial_when_ratio_low():
    issues = [IssueInfo(i, "t", "open", NOW, None, None) for i in range(4)]
    issues.append(IssueInfo(9, "t", "closed", NOW, None, None))
    assert check_issue_responsiveness(healthy_snapshot(issues=issues))[0] == PARTIAL


def test_pr_merges():
    assert check_pr_merges(healthy_snapshot(pulls=[]))[0] == FAIL


def test_ci_runs_states():
    assert check_ci_runs(bare_snapshot())[0] == FAIL
    s = healthy_snapshot(runs=[])
    assert check_ci_runs(s)[0] == PARTIAL  # workflows exist but no runs returned
    failing = healthy_snapshot(runs=[type(healthy_snapshot().runs[0])("CI", "completed", "failure", NOW, None)])
    assert check_ci_runs(failing)[0] == PARTIAL


def test_test_files_detects_common_layouts():
    layouts = [
        "tests/test_x.py",
        "src/__tests__/a.ts",
        "packages/web/button.test.tsx",
        "pkg/service_test.go",
        "spec/models/user_spec.rb",
    ]
    assert check_test_files(bare_snapshot(paths=layouts))[0] == PASS
    assert check_test_files(bare_snapshot(paths=["src/main.py"]))[0] == FAIL


def test_license_spdx_partial_when_file_unrecognised():
    s = bare_snapshot(paths=["LICENSE"], license_spdx="NOASSERTION")
    assert check_license_spdx(s)[0] == PARTIAL
    assert check_license_spdx(bare_snapshot(license_spdx="Apache-2.0"))[0] == PASS
