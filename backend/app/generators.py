"""Generate starter community files from what RepoRadar detected in a repository.

Every generated file contains ``<!-- TODO -->`` markers where the maintainer must
supply information RepoRadar cannot know (sponsors, contact details, ...).
Output is returned as ``{"files": [{"path", "content"}]}``.
"""

from __future__ import annotations

from dataclasses import dataclass

from .analyzer import RepoSnapshot, _basename


@dataclass(frozen=True)
class Stack:
    name: str
    runtime: str  # human-readable prerequisite, e.g. "Python 3.11+"
    install: str
    test: str


def detect_stack(s: RepoSnapshot) -> Stack:
    names = {_basename(p) for p in s.paths}
    if "package.json" in names:
        manager = "pnpm" if "pnpm-lock.yaml" in names else "yarn" if "yarn.lock" in names else "npm"
        return Stack("Node.js", "Node.js 20 or newer", f"{manager} install", f"{manager} test")
    if "pyproject.toml" in names:
        return Stack("Python", "Python 3.11 or newer", "pip install -e .[dev]", "pytest")
    if "requirements.txt" in names:
        return Stack("Python", "Python 3.11 or newer", "pip install -r requirements.txt", "pytest")
    if "go.mod" in names:
        return Stack("Go", "Go 1.22 or newer", "go mod download", "go test ./...")
    if "cargo.toml" in names:
        return Stack("Rust", "A stable Rust toolchain (rustup)", "cargo build", "cargo test")
    if "gemfile" in names:
        return Stack("Ruby", "Ruby 3.2 or newer", "bundle install", "bundle exec rake test")
    if "pom.xml" in names:
        return Stack("Java", "JDK 17 or newer", "mvn install -DskipTests", "mvn test")
    return Stack("Project", "<!-- TODO: required runtime and version -->", "<install command>", "<test command>")


def _title(s: RepoSnapshot) -> str:
    return s.name.replace("-", " ").replace("_", " ").title()


def generate_readme(s: RepoSnapshot) -> str:
    stack = detect_stack(s)
    description = s.description or "<!-- TODO: one-sentence description of what this project does -->"
    license_line = (
        f"This project is licensed under the {s.license_spdx} license. See [LICENSE](LICENSE)."
        if s.license_spdx and s.license_spdx != "NOASSERTION"
        else "This project is licensed under the terms in [LICENSE](LICENSE)."
    )
    return f"""# {_title(s)}

{description}

## Features

- <!-- TODO: list the 3-5 things this project does best -->

## Getting started

### Prerequisites

- {stack.runtime}

### Installation

```bash
git clone {s.html_url}.git
cd {s.name}
{stack.install}
```

## Usage

```bash
# <!-- TODO: the most common command or example -->
```

## Running the tests

```bash
{stack.test}
```

## Contributing

Contributions are welcome. Please read [CONTRIBUTING.md](CONTRIBUTING.md) before opening a pull request.

## License

{license_line}
"""


def generate_contributing(s: RepoSnapshot) -> str:
    stack = detect_stack(s)
    return f"""# Contributing to {_title(s)}

Thanks for taking the time to contribute! Every fix, doc improvement and idea helps.

## Code of conduct

Be kind and constructive. <!-- TODO: link to CODE_OF_CONDUCT.md if you have one -->

## Ways to contribute

- Report bugs using the bug report template.
- Suggest features using the feature request template.
- Improve documentation or examples.
- Pick up an issue labelled `good first issue`.

## Setting up your environment

1. Fork the repository and clone your fork.
2. Install dependencies:

   ```bash
   {stack.install}
   ```

## Running tests

```bash
{stack.test}
```

Please add or update tests for any behaviour you change.

## Style and commits

- Keep changes focused; one logical change per pull request.
- Write clear commit messages in the imperative mood, e.g. `Fix null check in parser`.
- <!-- TODO: formatter / linter commands and style rules -->

## Pull request process

1. Create a branch from `{s.default_branch}`.
2. Make your change and run the tests.
3. Open a pull request and fill in the pull request template.
4. A maintainer will review; please respond to feedback within a reasonable time.
"""


def generate_issue_templates(s: RepoSnapshot) -> list[dict[str, str]]:
    return [
        {
            "path": ".github/ISSUE_TEMPLATE/bug_report.md",
            "content": """---
name: Bug report
about: Something is not working as expected
labels: bug
---

## Describe the bug

A clear and concise description of the problem.

## Steps to reproduce

1. ...
2. ...

## Expected behaviour

## Actual behaviour

## Environment

- OS:
- Version or commit:
""",
        },
        {
            "path": ".github/ISSUE_TEMPLATE/feature_request.md",
            "content": """---
name: Feature request
about: Suggest an idea or improvement
labels: enhancement
---

## Problem

What problem would this solve? Who is affected?

## Proposed solution

## Alternatives considered

## Additional context
""",
        },
        {
            "path": ".github/ISSUE_TEMPLATE/config.yml",
            "content": f"blank_issues_enabled: false\ncontact_links:\n  - name: Questions and discussion\n    url: {s.html_url}/discussions\n    about: Ask questions in the discussions area.\n",
        },
    ]


def generate_pr_template(s: RepoSnapshot) -> list[dict[str, str]]:
    return [
        {
            "path": ".github/PULL_REQUEST_TEMPLATE.md",
            "content": """## Summary

<!-- What does this change do and why? -->

## Related issues

Closes #

## Checklist

- [ ] I have read CONTRIBUTING.md
- [ ] Tests pass locally
- [ ] I added or updated tests for this change
- [ ] Documentation is updated where needed
""",
        }
    ]


GENERATORS = {
    "readme": lambda s: [{"path": "README.md", "content": generate_readme(s)}],
    "contributing": lambda s: [{"path": "CONTRIBUTING.md", "content": generate_contributing(s)}],
    "issue-templates": generate_issue_templates,
    "pr-template": generate_pr_template,
}
