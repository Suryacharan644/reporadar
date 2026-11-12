"""Entry point for the RepoRadar GitHub Action.

Run with ``python -m app.action_runner`` from the ``backend/`` directory.

Environment (all set automatically by GitHub Actions except the optional ones):
  GITHUB_REPOSITORY        owner/name of the repository being checked
  GITHUB_TOKEN             token used to read the repo and post PR comments
  GITHUB_EVENT_PATH        event payload; used to find the pull request number
  GITHUB_STEP_SUMMARY      job summary file (optional)
  REPORADAR_MIN_SCORE      fail the job when the score is below this (default 0)
  REPORADAR_COMMENT        "false" to disable PR comments (default "true")
  REPORADAR_OUTPUT_DIR     where reporadar-report.{json,md} are written (default: cwd)

The analysis always targets the repository's default branch.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any

from .collector import collect_snapshot
from .github_client import GitHubClient, GitHubError
from .report import build_report, render_markdown
from .repo_input import parse_repo_input

COMMENT_MARKER = "<!-- reporadar-report -->"


def _pull_request_number(event_path: str | None) -> int | None:
    if not event_path or not Path(event_path).exists():
        return None
    event = json.loads(Path(event_path).read_text(encoding="utf-8"))
    pr = event.get("pull_request") or {}
    number = pr.get("number")
    return int(number) if number else None


async def _upsert_comment(gh: GitHubClient, owner: str, name: str, number: int, body: str) -> str:
    comments: list[dict[str, Any]] = await gh.list_issue_comments(owner, name, number)
    marked = [c for c in comments if COMMENT_MARKER in (c.get("body") or "")]
    if marked:
        await gh.update_comment(owner, name, marked[-1]["id"], body)
        return "updated"
    await gh.create_comment(owner, name, number, body)
    return "created"


async def run() -> int:
    repository = os.environ.get("GITHUB_REPOSITORY", "")
    if not repository:
        print("GITHUB_REPOSITORY is not set; this runner must run inside GitHub Actions.", file=sys.stderr)
        return 2
    token = os.environ.get("GITHUB_TOKEN") or None
    min_score = int(os.environ.get("REPORADAR_MIN_SCORE", "0") or 0)
    comment_enabled = os.environ.get("REPORADAR_COMMENT", "true").lower() != "false"

    ref = parse_repo_input(repository)
    async with GitHubClient(token) as gh:
        snapshot = await collect_snapshot(gh, ref)
        report = build_report(snapshot)
        markdown = render_markdown(report)

        output_dir = Path(os.environ.get("REPORADAR_OUTPUT_DIR") or os.getcwd())
        (output_dir / "reporadar-report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        (output_dir / "reporadar-report.md").write_text(markdown, encoding="utf-8")
        summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
        if summary_path:
            with open(summary_path, "a", encoding="utf-8") as fh:
                fh.write(markdown)

        number = _pull_request_number(os.environ.get("GITHUB_EVENT_PATH"))
        if number and comment_enabled:
            try:
                action = await _upsert_comment(
                    gh, ref.owner, ref.name, number, f"{COMMENT_MARKER}\n{markdown}"
                )
                print(f"RepoRadar comment {action} on pull request #{number}.")
            except GitHubError as exc:
                # Forked pull requests get a read-only token; report but do not fail the check.
                print(f"Could not post PR comment: {exc.message}", file=sys.stderr)

    score = report["score"]
    print(f"RepoRadar score for {ref.full_name}: {score}/100 (grade {report['grade']})")
    if score < min_score:
        print(f"Score {score} is below the required minimum of {min_score}.", file=sys.stderr)
        return 1
    return 0


def main() -> None:
    try:
        sys.exit(asyncio.run(run()))
    except GitHubError as exc:
        print(f"RepoRadar could not analyse the repository: {exc.message}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
