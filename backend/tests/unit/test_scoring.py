from app.analyzer import CATEGORIES, CHECKS, PARTIAL, PASS, FAIL, evaluate, grade_for, points_for
from tests.helpers import HEALTHY_README, bare_snapshot, healthy_snapshot


def test_category_weights_total_100():
    assert sum(weight for _, _, weight in CATEGORIES) == 100


def test_every_check_belongs_to_a_known_category():
    known = {cid for cid, _, _ in CATEGORIES}
    assert all(check.category in known for check in CHECKS)


def test_check_ids_are_unique():
    ids = [c.id for c in CHECKS]
    assert len(ids) == len(set(ids))


def test_healthy_repository_scores_100():
    ev = evaluate(healthy_snapshot())
    failing = [(c.id, c.evidence) for c in ev.checks if c.status != PASS]
    assert failing == []
    assert ev.score == 100
    assert ev.grade == "A"
    assert ev.summary == {"critical": 0, "warning": 0, "good": len(CHECKS)}


def test_bare_repository_scores_low_and_flags_critical_items():
    ev = evaluate(bare_snapshot())
    assert ev.score < 15
    critical_ids = {c.id for c in ev.checks if c.severity == "critical"}
    assert {"readme.exists", "license.file", "ci.workflows", "tests.files", "activity.recency"} <= critical_ids


def test_partial_points_are_half_rounded_down():
    assert points_for(PASS, 7) == 7
    assert points_for(PARTIAL, 7) == 3
    assert points_for(PARTIAL, 3) == 1
    assert points_for(FAIL, 7) == 0


def test_severity_rules():
    ev = evaluate(healthy_snapshot(paths=[p for p in healthy_snapshot().paths if p != "LICENSE"]))
    license_check = next(c for c in ev.checks if c.id == "license.file")
    assert license_check.status == FAIL
    assert license_check.severity == "critical"
    assert license_check.recommendation  # failures always carry a recommendation

    passing = next(c for c in ev.checks if c.id == "readme.exists")
    assert passing.severity == "good"
    assert passing.recommendation == ""


def test_non_critical_failure_is_a_warning():
    ev = evaluate(healthy_snapshot(contributing=None, paths=[p for p in healthy_snapshot().paths if p != "CONTRIBUTING.md"]))
    check = next(c for c in ev.checks if c.id == "contributing.file")
    assert check.status == FAIL
    assert check.severity == "warning"


def test_category_totals_match_check_totals():
    ev = evaluate(healthy_snapshot(readme=HEALTHY_README[:400]))
    for cat in ev.categories:
        assert cat.points == sum(c.points for c in ev.checks if c.category == cat.id)
        assert cat.max_points == sum(c.max_points for c in CHECKS if c.category == cat.id)
    assert sum(c.points for c in ev.checks) == ev.score


def test_grade_boundaries():
    assert grade_for(90) == "A"
    assert grade_for(89) == "B"
    assert grade_for(75) == "B"
    assert grade_for(74) == "C"
    assert grade_for(60) == "C"
    assert grade_for(59) == "D"
    assert grade_for(40) == "D"
    assert grade_for(39) == "F"
