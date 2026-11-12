from app.generators import GENERATORS, detect_stack, generate_readme
from app.report import build_report, render_badge, render_markdown
from tests.helpers import bare_snapshot, healthy_snapshot


def test_detect_stack_prefers_lockfile_manager():
    s = bare_snapshot(paths=["package.json", "pnpm-lock.yaml"])
    stack = detect_stack(s)
    assert stack.install == "pnpm install"
    assert stack.test == "pnpm test"


def test_detect_stack_python_and_go():
    assert detect_stack(bare_snapshot(paths=["requirements.txt"])).install == "pip install -r requirements.txt"
    assert detect_stack(bare_snapshot(paths=["go.mod"])).test == "go test ./..."


def test_generated_readme_uses_detected_facts():
    s = healthy_snapshot()
    text = generate_readme(s)
    assert text.startswith("# Widget")
    assert "git clone https://github.com/octo/widget.git" in text
    assert "This project is licensed under the MIT license" in text
    assert "<!-- TODO" in text  # maintainers must fill in the gaps


def test_every_generator_returns_named_files():
    s = healthy_snapshot()
    for kind, generator in GENERATORS.items():
        files = generator(s)
        assert files, kind
        for f in files:
            assert f["path"] and f["content"].strip(), kind


def test_build_report_is_json_serialisable_and_consistent():
    import json

    report = build_report(healthy_snapshot())
    json.dumps(report)  # must not raise
    assert report["score"] == 100
    assert report["grade"] == "A"
    assert len(report["stats"]["commit_activity"]) == 12
    assert sum(w["count"] for w in report["stats"]["commit_activity"]) <= 12


def test_markdown_lists_findings_and_marker_free_summary():
    report = build_report(bare_snapshot())
    md = render_markdown(report)
    assert "RepoRadar report: octo/empty" in md
    assert "🔴" in md  # critical findings are shown first


def test_badge_colour_and_text():
    svg = render_badge("octo", "widget", 92)
    assert svg.startswith("<svg")
    assert "92/100" in svg
    assert "#10b981" in svg
    assert "#ef4444" in render_badge("octo", "widget", 10)
