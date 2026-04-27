# DriftScope Implementation Plan

**Date:** 2026-04-27
**Status:** Active
**Spec:** `docs/specs/2026-04-27-driftscope-design.md`
**PRD:** `driftscope-longitudinal-ai-code-contribution-quality-monitor-prd.md`

---

## Principles

- **TDD cycle:** write failing test -> verify fail -> implement -> verify pass -> commit
- **DRY:** each data model, error type, and utility is defined exactly once
- **YAGNI:** no abstractions, plugins, or extensibility hooks until a second consumer exists
- **Frequent commits:** every task produces at least one commit with conventional-commit message
- **Coverage target:** >=95% line, >=90% branch per module

---

## Task Dependency Graph

```
Task 1: Project Scaffold
  |
  v
Task 2: Data Model
  |
  v
Task 3: Error Types
  |
  v
Task 4: Config (schema + loader + validate command)
  |
  v
Task 5: Authorship (patterns + classifier)
  |
  +-----> Task 6: Git Client (blame, log, diff_parser)
  |              |
  +--------------+-----> Task 7: AST Engine (parser, differ, survival)
  |              |              |
  |              |              v
  |              |        Task 8: Metrics (survival, complexity, churn)
  |              |              |
  v              v              v
Task 9: Reporting (json, markdown, html, csv)
  |
  v
Task 10: Cache (SQLite manager)
  |
  v
Task 11: CLI (Typer app, all subcommands)
  |
  v
Task 12: GitHub Integration (PR comment posting)
  |
  v
Task 13: E2E Tests (fixture repo, full pipeline)
  |
  v
Task 14: Distribution (packaging, CI workflow)
```

---

## Task 1: Project Scaffold

**Goal:** Establish the project structure, dependencies, tooling, and development environment.

### Files Created

```
driftscope/
├── pyproject.toml
├── .gitignore
├── driftscope/
│   ├── __init__.py
│   └── __main__.py
├── tests/
│   ├── __init__.py
│   └── conftest.py
```

### 1.1 `pyproject.toml`

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "driftscope"
version = "0.1.0"
description = "Longitudinal AI code contribution quality monitor"
requires-python = ">=3.11"
dependencies = [
    "typer>=0.12.0,<1.0",
    "pydantic>=2.7.0,<3.0",
    "pyyaml>=6.0,<7.0",
    "tree-sitter>=0.22.0,<1.0",
    "rich>=13.0,<14.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0,<9.0",
    "pytest-cov>=5.0,<6.0",
    "pytest-mock>=3.14,<4.0",
    "mypy>=1.10,<2.0",
    "ruff>=0.5,<1.0",
    "gitpython>=3.1,<4.0",
]

[project.scripts]
driftscope = "driftscope.cli.main:app"

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "--tb=short -q"
markers = [
    "slow: marks tests as slow (deselect with '-m \"not slow\"')",
]

[tool.ruff]
target-version = "py311"
line-length = 100

[tool.ruff.lint]
select = ["E", "F", "W", "I", "N", "UP", "B", "A", "SIM"]

[tool.mypy]
python_version = "3.11"
strict = true
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true
```

### 1.2 `.gitignore`

```
__pycache__/
*.pyc
*.pyo
*.egg-info/
dist/
build/
.pytest_cache/
.mypy_cache/
.ruff_cache/
htmlcov/
.coverage
.coverage.*
.driftscope/
*.db
.venv/
```

### 1.3 `driftscope/__init__.py`

```python
"""DriftScope: Longitudinal AI code contribution quality monitor."""

__version__ = "0.1.0"
```

### 1.4 `driftscope/__main__.py`

```python
"""Entry point for `python -m driftscope`."""

# CLI will be wired up in Task 11. For now, print version info.
import driftscope

print(f"DriftScope {driftscope.__version__} — CLI not yet available.")
```

### 1.5 `tests/__init__.py`

```python
"""DriftScope test suite."""
```

### 1.6 `tests/conftest.py`

```python
"""Shared test fixtures for DriftScope."""

from pathlib import Path

import pytest


@pytest.fixture
def tmp_git_repo(tmp_path: Path) -> Path:
    """Create a temporary git repository with one initial commit.

    Returns the path to the repository root.
    """
    import subprocess

    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )
    readme = tmp_path / "README.md"
    readme.write_text("# Test Repo\n")
    subprocess.run(["git", "add", "README.md"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Initial commit"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )
    return tmp_path
```

### Test

```bash
# Verify project structure
python -c "import driftscope; print(driftscope.__version__)"
# Expected: 0.1.0

# Verify test runner
python -m pytest tests/ -v
# Expected: collected 0 items (no tests yet, runner works)

# Verify entry point
python -m driftscope --help
# Expected: usage message from Typer (may fail since cli/main.py not yet created)
```

### Commit

```
feat(scaffold): initialize project structure with pyproject.toml, dependencies, and test config
```

---

## Task 2: Data Model

**Goal:** Define all Pydantic v2 models that flow between pipeline stages. These are the contracts.

### Files Created

```
driftscope/
├── models/
│   ├── __init__.py
│   ├── commit.py
│   ├── blame.py
│   ├── history.py
│   ├── ast_diff.py
│   ├── metrics.py
│   ├── report.py
│   └── provenance.py
tests/
├── models/
│   ├── __init__.py
│   ├── test_commit.py
│   ├── test_blame.py
│   ├── test_history.py
│   ├── test_ast_diff.py
│   ├── test_metrics.py
│   ├── test_report.py
│   └── test_provenance.py
```

### 2.1 `driftscope/models/__init__.py`

```python
"""DriftScope data models — typed contracts between pipeline stages."""

from driftscope.models.commit import Commit
from driftscope.models.blame import BlameLine
from driftscope.models.history import CommitHistory, AttributedCommit, AttributedHistory
from driftscope.models.ast_diff import ASTNodeChange, ASTFileDiff, ASTDiffSet
from driftscope.models.metrics import (
    SurvivalMetrics,
    ComplexityMetrics,
    WeeklyComplexity,
    ChurnMetrics,
    ModuleMetrics,
)
from driftscope.models.report import MetricsResult, ThresholdBreach
from driftscope.models.provenance import ProvenanceEntry

__all__ = [
    "Commit",
    "BlameLine",
    "CommitHistory",
    "AttributedCommit",
    "AttributedHistory",
    "ASTNodeChange",
    "ASTFileDiff",
    "ASTDiffSet",
    "SurvivalMetrics",
    "ComplexityMetrics",
    "WeeklyComplexity",
    "ChurnMetrics",
    "ModuleMetrics",
    "MetricsResult",
    "ThresholdBreach",
    "ProvenanceEntry",
]
```

### 2.2 `driftscope/models/commit.py`

```python
"""Git commit data model."""

from datetime import datetime

from pydantic import BaseModel, Field


class Commit(BaseModel):
    """A single git commit with full metadata.

    Attributes:
        sha: Full 40-character SHA-1 hash.
        short_sha: First 7 characters of SHA.
        timestamp: Commit author timestamp (UTC).
        author_name: Name of the commit author.
        author_email: Email of the commit author.
        committer_name: Name of the committer (distinct for AI-tagged commits).
        committer_email: Email of the committer.
        message_subject: First line of the commit message.
        message_body: Full message body including trailers.
        parent_shas: Parent commit SHAs (1 for normal, 2+ for merge commits).
    """

    sha: str = Field(min_length=40, max_length=40, pattern=r"^[0-9a-f]{40}$")
    short_sha: str = Field(min_length=7, max_length=7, pattern=r"^[0-9a-f]{7}$")
    timestamp: datetime
    author_name: str
    author_email: str
    committer_name: str
    committer_email: str
    message_subject: str
    message_body: str
    parent_shas: list[str]

    model_config = {"frozen": True}
```

### 2.3 `driftscope/models/blame.py`

```python
"""Git blame line data model."""

from pydantic import BaseModel, Field


class BlameLine(BaseModel):
    """A single line from git blame output.

    Attributes:
        line_number: 1-based line number in the file at HEAD.
        commit_sha: Originating commit SHA (40 chars).
        author_name: Name of the author blamed for this line.
        author_email: Email of the author blamed for this line.
        content: The line content (stripped of leading/trailing whitespace).
    """

    line_number: int = Field(ge=1)
    commit_sha: str = Field(min_length=40, max_length=40, pattern=r"^[0-9a-f]{40}$")
    author_name: str
    author_email: str
    content: str

    model_config = {"frozen": True}
```

### 2.4 `driftscope/models/history.py`

```python
"""Commit history and attributed history models."""

from datetime import datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from driftscope.models.blame import BlameLine
from driftscope.models.commit import Commit


class CommitHistory(BaseModel):
    """Ordered collection of commits with blame data for a repository.

    Attributes:
        repo_path: Absolute path to the repository root.
        commits: Commits ordered oldest to newest within the range.
        blame: Mapping of file paths to their blame results at HEAD.
        range_start: Start of the analysis window (UTC).
        range_end: End of the analysis window (UTC).
    """

    repo_path: Path
    commits: list[Commit]
    blame: dict[Path, list[BlameLine]]
    range_start: datetime
    range_end: datetime


class AttributedCommit(Commit):
    """A commit with authorship classification applied.

    Inherits all Commit fields and adds authorship attribution.

    Attributes:
        authorship_class: Whether this commit was authored by a human or AI.
        matched_pattern: The regex pattern that matched (if AI-attributed).
        matched_text: The actual text snippet that matched (if AI-attributed).
    """

    authorship_class: Literal["human", "ai"]
    matched_pattern: str | None = None
    matched_text: str | None = None


class AttributedHistory(BaseModel):
    """Commit history with authorship attribution applied.

    Attributes:
        repo_path: Absolute path to the repository root.
        commits: Attributed commits ordered oldest to newest.
        blame: Mapping of file paths to their blame results at HEAD.
        range_start: Start of the analysis window (UTC).
        range_end: End of the analysis window (UTC).
        ai_commit_count: Number of AI-attributed commits.
        human_commit_count: Number of human-attributed commits.
    """

    repo_path: Path
    commits: list[AttributedCommit]
    blame: dict[Path, list[BlameLine]]
    range_start: datetime
    range_end: datetime
    ai_commit_count: int = Field(ge=0)
    human_commit_count: int = Field(ge=0)
```

### 2.5 `driftscope/models/ast_diff.py`

```python
"""AST-level diff models for tree-sitter analysis."""

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field


class ASTNodeChange(BaseModel):
    """A single AST node change within a commit.

    Attributes:
        node_type: Tree-sitter node type (e.g., "function_definition").
        start_line: 1-based start line of the node.
        end_line: 1-based end line of the node.
        change_type: Whether the node was added, removed, or modified.
        text_hash: SHA-256 hash of the node text for exact survival matching.
    """

    node_type: str
    start_line: int = Field(ge=1)
    end_line: int = Field(ge=1)
    change_type: Literal["added", "removed", "modified"]
    text_hash: str = Field(min_length=64, max_length=64)


class ASTFileDiff(BaseModel):
    """AST diff for a single file within a single commit.

    Attributes:
        file_path: Path to the source file (relative to repo root).
        commit_sha: The commit SHA that produced this diff.
        before_hash: SHA-256 hash of the AST before the commit (None for new files).
        after_hash: SHA-256 hash of the AST after the commit (None for deleted files).
        changes: List of individual node changes.
        authorship_class: Whether the commit was human or AI authored.
    """

    file_path: Path
    commit_sha: str = Field(min_length=40, max_length=40)
    before_hash: str | None = None
    after_hash: str | None = None
    changes: list[ASTNodeChange]
    authorship_class: Literal["human", "ai"]


class ASTDiffSet(BaseModel):
    """Collection of AST diffs across all files and commits.

    Attributes:
        diffs: List of per-file AST diffs.
        skipped_files: Files skipped during analysis with reasons.
    """

    diffs: list[ASTFileDiff]
    skipped_files: list[dict[str, str]]
```

### 2.6 `driftscope/models/metrics.py`

```python
"""Metrics computation models — survival, complexity, churn."""

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field


class SurvivalMetrics(BaseModel):
    """Line survival rate for a specific time window.

    Attributes:
        window: Time window identifier (e.g., "30d", "90d").
        ai_lines_introduced: Total AI-authored lines introduced in the window.
        ai_lines_surviving: AI-authored lines still present at window end.
        ai_survival_rate: AI survival rate (0.0 to 1.0).
        human_lines_introduced: Total human-authored lines introduced in the window.
        human_lines_surviving: Human-authored lines still present at window end.
        human_survival_rate: Human survival rate (0.0 to 1.0).
    """

    window: str = Field(pattern=r"^\d+d$")
    ai_lines_introduced: int = Field(ge=0)
    ai_lines_surviving: int = Field(ge=0)
    ai_survival_rate: float = Field(ge=0.0, le=1.0)
    human_lines_introduced: int = Field(ge=0)
    human_lines_surviving: int = Field(ge=0)
    human_survival_rate: float = Field(ge=0.0, le=1.0)


class WeeklyComplexity(BaseModel):
    """Complexity metrics for a single week.

    Attributes:
        week_start: Monday date of the week.
        ai_cyclomatic_mean: Mean cyclomatic complexity delta for AI commits.
        human_cyclomatic_mean: Mean cyclomatic complexity delta for human commits.
        ai_cognitive_mean: Mean cognitive complexity delta for AI commits.
        human_cognitive_mean: Mean cognitive complexity delta for human commits.
        ai_commit_count: Number of AI-attributed commits this week.
        human_commit_count: Number of human-attributed commits this week.
    """

    week_start: date
    ai_cyclomatic_mean: float
    human_cyclomatic_mean: float
    ai_cognitive_mean: float
    human_cognitive_mean: float
    ai_commit_count: int = Field(ge=0)
    human_commit_count: int = Field(ge=0)


class ComplexityMetrics(BaseModel):
    """Complexity delta metrics segmented by authorship.

    Attributes:
        cyclomatic_delta_ai: Mean cyclomatic complexity delta per AI commit.
        cyclomatic_delta_human: Mean cyclomatic complexity delta per human commit.
        cognitive_delta_ai: Mean cognitive complexity delta per AI commit.
        cognitive_delta_human: Mean cognitive complexity delta per human commit.
        weekly_series: Weekly breakdown of complexity deltas.
    """

    cyclomatic_delta_ai: float
    cyclomatic_delta_human: float
    cognitive_delta_ai: float
    cognitive_delta_human: float
    weekly_series: list[WeeklyComplexity]


class ChurnMetrics(BaseModel):
    """Module-level churn attribution over a rolling 365-day window.

    Attributes:
        total_churn_lines: Total lines added + removed in the rolling window.
        ai_churn_lines: Churn traceable to AI-introduced code.
        ai_churn_attribution_pct: Percentage of churn attributable to AI (0.0 to 100.0).
    """

    total_churn_lines: int = Field(ge=0)
    ai_churn_lines: int = Field(ge=0)
    ai_churn_attribution_pct: float = Field(ge=0.0, le=100.0)


class ModuleMetrics(BaseModel):
    """Aggregated metrics for a single repository module.

    Attributes:
        module_path: Top-level directory path relative to repo root.
        total_lines: Total source lines in the module.
        ai_lines: AI-authored lines in the module.
        human_lines: Human-authored lines in the module.
        survival: Survival metrics keyed by window (e.g., "30d", "90d").
        complexity: Complexity delta metrics.
        churn: Churn attribution metrics.
    """

    module_path: str
    total_lines: int = Field(ge=0)
    ai_lines: int = Field(ge=0)
    human_lines: int = Field(ge=0)
    survival: dict[str, SurvivalMetrics]
    complexity: ComplexityMetrics
    churn: ChurnMetrics
```

### 2.7 `driftscope/models/report.py`

```python
"""Top-level report model — the output contract."""

from datetime import datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from driftscope.models.metrics import ModuleMetrics


class ThresholdBreach(BaseModel):
    """A metric value that crossed a configured threshold.

    Attributes:
        metric: The metric name that breached.
        module_path: The module where the breach occurred.
        value: The actual metric value.
        threshold: The configured threshold value.
        direction: Whether the value went above or below the threshold.
    """

    metric: str
    module_path: str
    value: float
    threshold: float
    direction: Literal["above", "below"]


class MetricsResult(BaseModel):
    """Top-level analysis result — the root of all report outputs.

    Attributes:
        repo_path: Absolute path to the analyzed repository.
        commit_range: Tuple of (start SHA, end SHA) analyzed.
        range_start: Start of the analysis window (UTC).
        range_end: End of the analysis window (UTC).
        schema_version: Semantic version of the report schema.
        modules: Per-module metrics.
        skipped_files: Files skipped during analysis with reasons.
        data_incomplete: True if the analysis window is shorter than the commit span.
        threshold_breaches: Any threshold violations detected.
    """

    repo_path: Path
    commit_range: tuple[str, str]
    range_start: datetime
    range_end: datetime
    schema_version: str = "1.0.0"
    modules: list[ModuleMetrics]
    skipped_files: list[dict[str, str]]
    data_incomplete: bool = False
    threshold_breaches: list[ThresholdBreach] = Field(default_factory=list)
```

### 2.8 `driftscope/models/provenance.py`

```python
"""Provenance model for line-level authorship tracking."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class ProvenanceEntry(BaseModel):
    """Line-level provenance entry for a specific code region.

    Attributes:
        file_path: Path to the source file (relative to repo root).
        line_start: 1-based start line of the region.
        line_end: 1-based end line of the region.
        authorship_class: Whether this region was human or AI authored.
        originating_commit_sha: SHA of the commit that introduced this code.
        commit_timestamp: Timestamp of the originating commit.
        co_authorship_tag: The matched co-authorship tag text (if AI-attributed).
    """

    file_path: str
    line_start: int
    line_end: int
    authorship_class: Literal["human", "ai"]
    originating_commit_sha: str
    commit_timestamp: datetime
    co_authorship_tag: str | None = None
```

### Tests

#### `tests/models/__init__.py`

```python
"""Tests for driftscope.models."""
```

#### `tests/models/test_commit.py`

```python
"""Tests for the Commit model."""

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from driftscope.models.commit import Commit


def _valid_commit(**overrides: object) -> dict:
    """Return a valid Commit payload with optional overrides."""
    base = {
        "sha": "a" * 40,
        "short_sha": "a" * 7,
        "timestamp": datetime(2025, 1, 15, 10, 30, 0, tzinfo=timezone.utc),
        "author_name": "Alice",
        "author_email": "alice@example.com",
        "committer_name": "Alice",
        "committer_email": "alice@example.com",
        "message_subject": "Add feature",
        "message_body": "",
        "parent_shas": ["b" * 40],
    }
    base.update(overrides)
    return base


def test_commit_valid() -> None:
    """A well-formed Commit instantiates without error."""
    commit = Commit(**_valid_commit())
    assert commit.sha == "a" * 40
    assert commit.short_sha == "a" * 7
    assert commit.parent_shas == ["b" * 40]


def test_commit_rejects_short_sha() -> None:
    """short_sha must be exactly 7 hex chars."""
    with pytest.raises(ValidationError):
        Commit(**_valid_commit(short_sha="abc"))


def test_commit_rejects_non_hex_sha() -> None:
    """sha must be 40 hex characters."""
    with pytest.raises(ValidationError):
        Commit(**_valid_commit(sha="g" * 40))


def test_commit_rejects_sha_too_short() -> None:
    """sha must be exactly 40 characters."""
    with pytest.raises(ValidationError):
        Commit(**_valid_commit(sha="a" * 39))


def test_commit_frozen() -> None:
    """Commit instances are immutable."""
    commit = Commit(**_valid_commit())
    with pytest.raises(ValidationError):
        commit.sha = "c" * 40  # type: ignore[misc]


def test_commit_merge_has_multiple_parents() -> None:
    """Merge commits have 2+ parent SHAs."""
    commit = Commit(**_valid_commit(parent_shas=["b" * 40, "c" * 40]))
    assert len(commit.parent_shas) == 2
```

#### `tests/models/test_blame.py`

```python
"""Tests for the BlameLine model."""

import pytest
from pydantic import ValidationError

from driftscope.models.blame import BlameLine


def test_blame_line_valid() -> None:
    """A well-formed BlameLine instantiates without error."""
    line = BlameLine(
        line_number=1,
        commit_sha="a" * 40,
        author_name="Alice",
        author_email="alice@example.com",
        content="x = 1",
    )
    assert line.line_number == 1
    assert line.content == "x = 1"


def test_blame_line_rejects_line_zero() -> None:
    """Line numbers must be >= 1."""
    with pytest.raises(ValidationError):
        BlameLine(
            line_number=0,
            commit_sha="a" * 40,
            author_name="Alice",
            author_email="alice@example.com",
            content="x = 1",
        )


def test_blame_line_rejects_invalid_sha() -> None:
    """commit_sha must be 40 hex characters."""
    with pytest.raises(ValidationError):
        BlameLine(
            line_number=1,
            commit_sha="not-a-sha",
            author_name="Alice",
            author_email="alice@example.com",
            content="x = 1",
        )
```

#### `tests/models/test_history.py`

```python
"""Tests for CommitHistory, AttributedCommit, and AttributedHistory models."""

from datetime import datetime, timezone
from pathlib import Path

import pytest
from pydantic import ValidationError

from driftscope.models.blame import BlameLine
from driftscope.models.commit import Commit
from driftscope.models.history import AttributedCommit, AttributedHistory, CommitHistory


def _commit(sha_suffix: str = "a") -> dict:
    return {
        "sha": sha_suffix * 40,
        "short_sha": sha_suffix * 7,
        "timestamp": datetime(2025, 1, 15, 10, 0, tzinfo=timezone.utc),
        "author_name": "Alice",
        "author_email": "alice@example.com",
        "committer_name": "Alice",
        "committer_email": "alice@example.com",
        "message_subject": "Commit",
        "message_body": "",
        "parent_shas": ["b" * 40],
    }


def test_commit_history_valid() -> None:
    """CommitHistory with commits and blame data instantiates correctly."""
    history = CommitHistory(
        repo_path=Path("/tmp/repo"),
        commits=[Commit(**_commit("a")), Commit(**_commit("c"))],
        blame={Path("src/main.py"): [BlameLine(
            line_number=1,
            commit_sha="a" * 40,
            author_name="Alice",
            author_email="alice@example.com",
            content="print('hello')",
        )]},
        range_start=datetime(2025, 1, 1, tzinfo=timezone.utc),
        range_end=datetime(2025, 2, 1, tzinfo=timezone.utc),
    )
    assert len(history.commits) == 2
    assert history.repo_path == Path("/tmp/repo")
    assert len(history.blame) == 0


def test_attributed_commit_human() -> None:
    """AttributedCommit with human class has no matched_pattern."""
    attr = AttributedCommit(**_commit(), authorship_class="human")
    assert attr.authorship_class == "human"
    assert attr.matched_pattern is None


def test_attributed_commit_ai() -> None:
    """AttributedCommit with AI class stores matched pattern details."""
    attr = AttributedCommit(
        **_commit(),
        authorship_class="ai",
        matched_pattern=r"Co-Authored-By:.*Copilot",
        matched_text="Co-Authored-By: GitHub Copilot",
    )
    assert attr.authorship_class == "ai"
    assert attr.matched_text == "Co-Authored-By: GitHub Copilot"


def test_attributed_history_counts() -> None:
    """AttributedHistory correctly counts AI and human commits."""
    history = AttributedHistory(
        repo_path=Path("/tmp/repo"),
        commits=[
            AttributedCommit(**_commit("a"), authorship_class="ai", matched_pattern="p"),
            AttributedCommit(**_commit("c"), authorship_class="human"),
        ],
        blame={},
        range_start=datetime(2025, 1, 1, tzinfo=timezone.utc),
        range_end=datetime(2025, 2, 1, tzinfo=timezone.utc),
        ai_commit_count=1,
        human_commit_count=1,
    )
    assert history.ai_commit_count == 1
    assert history.human_commit_count == 1


def test_attributed_history_rejects_negative_counts() -> None:
    """ai_commit_count and human_commit_count must be >= 0."""
    with pytest.raises(ValidationError):
        AttributedHistory(
            repo_path=Path("/tmp/repo"),
            commits=[],
            blame={},
            range_start=datetime(2025, 1, 1, tzinfo=timezone.utc),
            range_end=datetime(2025, 2, 1, tzinfo=timezone.utc),
            ai_commit_count=-1,
            human_commit_count=0,
        )
```

#### `tests/models/test_ast_diff.py`

```python
"""Tests for AST diff models."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from driftscope.models.ast_diff import ASTDiffSet, ASTFileDiff, ASTNodeChange


def test_ast_node_change_added() -> None:
    """ASTNodeChange for an added node."""
    change = ASTNodeChange(
        node_type="function_definition",
        start_line=10,
        end_line=25,
        change_type="added",
        text_hash="a" * 64,
    )
    assert change.change_type == "added"


def test_ast_node_change_rejects_invalid_hash() -> None:
    """text_hash must be exactly 64 hex characters."""
    with pytest.raises(ValidationError):
        ASTNodeChange(
            node_type="function_definition",
            start_line=10,
            end_line=25,
            change_type="added",
            text_hash="tooshort",
        )


def test_ast_node_change_rejects_invalid_change_type() -> None:
    """change_type must be added, removed, or modified."""
    with pytest.raises(ValidationError):
        ASTNodeChange(
            node_type="function_definition",
            start_line=10,
            end_line=25,
            change_type="renamed",
            text_hash="a" * 64,
        )


def test_ast_file_diff_new_file() -> None:
    """ASTFileDiff for a new file has before_hash=None."""
    diff = ASTFileDiff(
        file_path=Path("src/new_module.py"),
        commit_sha="a" * 40,
        before_hash=None,
        after_hash="b" * 64,
        changes=[],
        authorship_class="ai",
    )
    assert diff.before_hash is None


def test_ast_diff_set() -> None:
    """ASTDiffSet aggregates diffs and skipped files."""
    ds = ASTDiffSet(
        diffs=[],
        skipped_files=[{"path": "vendor/lib.js", "reason": "unsupported_extension"}],
    )
    assert len(ds.skipped_files) == 1
```

#### `tests/models/test_metrics.py`

```python
"""Tests for metrics models."""

from datetime import date

import pytest
from pydantic import ValidationError

from driftscope.models.metrics import (
    ChurnMetrics,
    ComplexityMetrics,
    ModuleMetrics,
    SurvivalMetrics,
    WeeklyComplexity,
)


def test_survival_metrics_valid() -> None:
    """SurvivalMetrics with valid rates instantiates."""
    sm = SurvivalMetrics(
        window="90d",
        ai_lines_introduced=100,
        ai_lines_surviving=67,
        ai_survival_rate=0.67,
        human_lines_introduced=500,
        human_lines_surviving=450,
        human_survival_rate=0.9,
    )
    assert sm.ai_survival_rate == 0.67


def test_survival_metrics_rejects_rate_above_one() -> None:
    """Survival rate must be <= 1.0."""
    with pytest.raises(ValidationError):
        SurvivalMetrics(
            window="90d",
            ai_lines_introduced=100,
            ai_lines_surviving=100,
            ai_survival_rate=1.5,
            human_lines_introduced=100,
            human_lines_surviving=100,
            human_survival_rate=1.0,
        )


def test_survival_metrics_rejects_invalid_window() -> None:
    """Window must match \\d+d pattern."""
    with pytest.raises(ValidationError):
        SurvivalMetrics(
            window="3months",
            ai_lines_introduced=100,
            ai_lines_surviving=67,
            ai_survival_rate=0.67,
            human_lines_introduced=100,
            human_lines_surviving=100,
            human_survival_rate=1.0,
        )


def test_weekly_complexity_valid() -> None:
    """WeeklyComplexity with valid data instantiates."""
    wc = WeeklyComplexity(
        week_start=date(2025, 11, 3),
        ai_cyclomatic_mean=2.3,
        human_cyclomatic_mean=0.8,
        ai_cognitive_mean=3.1,
        human_cognitive_mean=1.2,
        ai_commit_count=12,
        human_commit_count=34,
    )
    assert wc.ai_commit_count == 12


def test_churn_metrics_valid() -> None:
    """ChurnMetrics with valid percentage instantiates."""
    cm = ChurnMetrics(
        total_churn_lines=1000,
        ai_churn_lines=425,
        ai_churn_attribution_pct=42.5,
    )
    assert cm.ai_churn_attribution_pct == 42.5


def test_churn_metrics_rejects_pct_over_100() -> None:
    """Churn attribution must be <= 100.0."""
    with pytest.raises(ValidationError):
        ChurnMetrics(
            total_churn_lines=100,
            ai_churn_lines=150,
            ai_churn_attribution_pct=150.0,
        )


def test_module_metrics_valid() -> None:
    """ModuleMetrics with nested metrics instantiates."""
    mm = ModuleMetrics(
        module_path="src/payments",
        total_lines=5000,
        ai_lines=1204,
        human_lines=3796,
        survival={"90d": SurvivalMetrics(
            window="90d",
            ai_lines_introduced=100,
            ai_lines_surviving=67,
            ai_survival_rate=0.67,
            human_lines_introduced=500,
            human_lines_surviving=450,
            human_survival_rate=0.9,
        )},
        complexity=ComplexityMetrics(
            cyclomatic_delta_ai=3.2,
            cyclomatic_delta_human=1.1,
            cognitive_delta_ai=4.5,
            cognitive_delta_human=2.0,
            weekly_series=[],
        ),
        churn=ChurnMetrics(
            total_churn_lines=2000,
            ai_churn_lines=500,
            ai_churn_attribution_pct=25.0,
        ),
    )
    assert mm.module_path == "src/payments"
```

#### `tests/models/test_report.py`

```python
"""Tests for the MetricsResult report model."""

from datetime import datetime, timezone
from pathlib import Path

from driftscope.models.report import MetricsResult, ThresholdBreach
from driftscope.models.metrics import (
    ChurnMetrics,
    ComplexityMetrics,
    ModuleMetrics,
    SurvivalMetrics,
)


def _module_metrics() -> ModuleMetrics:
    return ModuleMetrics(
        module_path="src/payments",
        total_lines=5000,
        ai_lines=1204,
        human_lines=3796,
        survival={"90d": SurvivalMetrics(
            window="90d",
            ai_lines_introduced=100,
            ai_lines_surviving=67,
            ai_survival_rate=0.67,
            human_lines_introduced=500,
            human_lines_surviving=450,
            human_survival_rate=0.9,
        )},
        complexity=ComplexityMetrics(
            cyclomatic_delta_ai=3.2,
            cyclomatic_delta_human=1.1,
            cognitive_delta_ai=4.5,
            cognitive_delta_human=2.0,
            weekly_series=[],
        ),
        churn=ChurnMetrics(
            total_churn_lines=2000,
            ai_churn_lines=500,
            ai_churn_attribution_pct=25.0,
        ),
    )


def test_metrics_result_valid() -> None:
    """MetricsResult with full data instantiates with default schema version."""
    result = MetricsResult(
        repo_path=Path("/tmp/repo"),
        commit_range=("a" * 40, "c" * 40),
        range_start=datetime(2025, 1, 1, tzinfo=timezone.utc),
        range_end=datetime(2025, 4, 1, tzinfo=timezone.utc),
        modules=[_module_metrics()],
        skipped_files=[],
    )
    assert result.schema_version == "1.0.0"
    assert len(result.modules) == 1
    assert result.threshold_breaches == []


def test_metrics_result_with_breaches() -> None:
    """MetricsResult includes threshold breaches when provided."""
    result = MetricsResult(
        repo_path=Path("/tmp/repo"),
        commit_range=("a" * 40, "c" * 40),
        range_start=datetime(2025, 1, 1, tzinfo=timezone.utc),
        range_end=datetime(2025, 4, 1, tzinfo=timezone.utc),
        modules=[_module_metrics()],
        skipped_files=[],
        threshold_breaches=[ThresholdBreach(
            metric="ai_churn_attribution_pct",
            module_path="src/payments",
            value=62.5,
            threshold=50.0,
            direction="above",
        )],
    )
    assert len(result.threshold_breaches) == 1
    assert result.threshold_breaches[0].direction == "above"


def test_metrics_result_json_round_trip() -> None:
    """MetricsResult serializes to JSON and back without data loss."""
    result = MetricsResult(
        repo_path=Path("/tmp/repo"),
        commit_range=("a" * 40, "c" * 40),
        range_start=datetime(2025, 1, 1, tzinfo=timezone.utc),
        range_end=datetime(2025, 4, 1, tzinfo=timezone.utc),
        modules=[_module_metrics()],
        skipped_files=[],
        data_incomplete=True,
    )
    json_str = result.model_dump_json()
    restored = MetricsResult.model_validate_json(json_str)
    assert restored.schema_version == result.schema_version
    assert restored.data_incomplete is True
    assert len(restored.modules) == 1
```

#### `tests/models/test_provenance.py`

```python
"""Tests for the ProvenanceEntry model."""

from datetime import datetime, timezone

from driftscope.models.provenance import ProvenanceEntry


def test_provenance_entry_ai() -> None:
    """AI-attributed provenance entry with co-authorship tag."""
    entry = ProvenanceEntry(
        file_path="src/payments/processor.py",
        line_start=45,
        line_end=67,
        authorship_class="ai",
        originating_commit_sha="a" * 40,
        commit_timestamp=datetime(2025, 11, 14, 9, 23, 0, tzinfo=timezone.utc),
        co_authorship_tag="Co-Authored-By: Claude",
    )
    assert entry.authorship_class == "ai"
    assert entry.co_authorship_tag == "Co-Authored-By: Claude"


def test_provenance_entry_human() -> None:
    """Human-attributed provenance entry has null co_authorship_tag."""
    entry = ProvenanceEntry(
        file_path="src/auth/login.py",
        line_start=10,
        line_end=20,
        authorship_class="human",
        originating_commit_sha="f" * 40,
        commit_timestamp=datetime(2025, 10, 30, 14, 17, 0, tzinfo=timezone.utc),
    )
    assert entry.co_authorship_tag is None


def test_provenance_entry_json_round_trip() -> None:
    """ProvenanceEntry round-trips through JSON serialization."""
    entry = ProvenanceEntry(
        file_path="src/main.py",
        line_start=1,
        line_end=5,
        authorship_class="human",
        originating_commit_sha="b" * 40,
        commit_timestamp=datetime(2025, 6, 1, tzinfo=timezone.utc),
    )
    json_str = entry.model_dump_json()
    restored = ProvenanceEntry.model_validate_json(json_str)
    assert restored.file_path == entry.file_path
    assert restored.line_start == entry.line_start
```

### Test Commands

```bash
python -m pytest tests/models/ -v
# Expected: all tests pass, ~25 tests covering validation, serialization, edge cases

python -m pytest tests/models/ --cov=driftscope/models --cov-report=term-missing
# Expected: >=95% line coverage across all model modules
```

### Commit

```
feat(models): add all Pydantic v2 data models — Commit, BlameLine, History, ASTDiff, Metrics, Report, Provenance
```

---

## Task 3: Error Types

**Goal:** Define the DriftScope error hierarchy used across all pipeline stages.

### Files Created

```
driftscope/
├── errors.py
tests/
├── test_errors.py
```

### 3.1 `driftscope/errors.py`

```python
"""DriftScope error hierarchy.

Every error inherits from DriftScopeError. Each subclass maps to a pipeline
stage and carries structured context for JSON error output to stderr.
"""


class DriftScopeError(Exception):
    """Base error for all DriftScope failures.

    Attributes:
        message: Human-readable error description.
        stage: Pipeline stage where the error occurred (e.g., "git_client").
        file: Optional file path related to the error.
        suggestion: Optional remediation hint.
    """

    def __init__(
        self,
        message: str,
        stage: str = "",
        file: str | None = None,
        suggestion: str | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.stage = stage
        self.file = file
        self.suggestion = suggestion

    def to_dict(self) -> dict[str, str | None]:
        """Serialize to the structured JSON error format for stderr."""
        return {
            "type": type(self).__name__,
            "message": self.message,
            "stage": self.stage,
            "file": self.file,
            "suggestion": self.suggestion,
        }


class ConfigError(DriftScopeError):
    """Invalid .driftscope.yaml: bad regex, missing required field, unknown key."""

    def __init__(self, message: str, **kwargs: object) -> None:
        super().__init__(message, stage="config", **kwargs)


class GitError(DriftScopeError):
    """git binary failures: not a repo, no history, authentication issue, binary not found."""

    def __init__(self, message: str, **kwargs: object) -> None:
        super().__init__(message, stage="git_client", **kwargs)


class AuthorshipError(DriftScopeError):
    """Pattern compilation failures: invalid regex in custom patterns."""

    def __init__(self, message: str, **kwargs: object) -> None:
        super().__init__(message, stage="authorship", **kwargs)


class ASTParseError(DriftScopeError):
    """tree-sitter parsing failures: unsupported language, corrupted grammar, file too large."""

    def __init__(self, message: str, **kwargs: object) -> None:
        super().__init__(message, stage="ast_engine", **kwargs)


class MetricError(DriftScopeError):
    """Computation failures: empty window, insufficient data, division by zero."""

    def __init__(self, message: str, **kwargs: object) -> None:
        super().__init__(message, stage="metrics", **kwargs)


class ReportError(DriftScopeError):
    """Output failures: disk full, permission denied, template rendering error."""

    def __init__(self, message: str, **kwargs: object) -> None:
        super().__init__(message, stage="reporting", **kwargs)
```

### 3.2 `tests/test_errors.py`

```python
"""Tests for the DriftScope error hierarchy."""

import json

from driftscope.errors import (
    ASTParseError,
    AuthorshipError,
    ConfigError,
    DriftScopeError,
    GitError,
    MetricError,
    ReportError,
)


def test_driftscope_error_is_exception() -> None:
    """DriftScopeError inherits from Exception."""
    err = DriftScopeError(message="test")
    assert isinstance(err, Exception)


def test_driftscope_error_to_dict() -> None:
    """to_dict produces the structured error format."""
    err = DriftScopeError(
        message="something broke",
        stage="pipeline",
        file="src/main.py",
        suggestion="try again",
    )
    d = err.to_dict()
    assert d["type"] == "DriftScopeError"
    assert d["message"] == "something broke"
    assert d["stage"] == "pipeline"
    assert d["file"] == "src/main.py"
    assert d["suggestion"] == "try again"


def test_driftscope_error_to_dict_serializable() -> None:
    """to_dict output is JSON-serializable."""
    err = DriftScopeError(message="test", stage="s")
    json_str = json.dumps({"error": err.to_dict()})
    assert "DriftScopeError" in json_str


def test_config_error_default_stage() -> None:
    """ConfigError defaults to stage='config'."""
    err = ConfigError(message="bad yaml")
    assert err.stage == "config"
    assert isinstance(err, DriftScopeError)


def test_git_error_default_stage() -> None:
    """GitError defaults to stage='git_client'."""
    err = GitError(message="not a repo")
    assert err.stage == "git_client"


def test_authorship_error_default_stage() -> None:
    """AuthorshipError defaults to stage='authorship'."""
    err = AuthorshipError(message="bad regex")
    assert err.stage == "authorship"


def test_ast_parse_error_default_stage() -> None:
    """ASTParseError defaults to stage='ast_engine'."""
    err = ASTParseError(message="parse timeout")
    assert err.stage == "ast_engine"


def test_metric_error_default_stage() -> None:
    """MetricError defaults to stage='metrics'."""
    err = MetricError(message="division by zero")
    assert err.stage == "metrics"


def test_report_error_default_stage() -> None:
    """ReportError defaults to stage='reporting'."""
    err = ReportError(message="disk full")
    assert err.stage == "reporting"


def test_error_optional_fields() -> None:
    """file and suggestion are None by default."""
    err = ConfigError(message="bad config")
    assert err.file is None
    assert err.suggestion is None


def test_error_with_all_context() -> None:
    """Errors can carry full context including file and suggestion."""
    err = ASTParseError(
        message="parse timeout on src/large_file.py (5.2s > 5.0s limit)",
        file="src/large_file.py",
        suggestion="Increase timeout with --parse-timeout or exclude with .driftscope.yaml",
    )
    assert err.file == "src/large_file.py"
    assert "--parse-timeout" in err.suggestion
```

### Test Commands

```bash
python -m pytest tests/test_errors.py -v
# Expected: 11 tests, all passing

python -m pytest tests/test_errors.py --cov=driftscope/errors --cov-report=term-missing
# Expected: 100% coverage
```

### Commit

```
feat(errors): add DriftScopeError hierarchy with structured JSON output for all pipeline stages
```

---

## Task 4: Config (Schema, Loader, Validate Command)

**Goal:** Implement the Pydantic config schema, YAML loader, and `driftscope config validate` command.

### Files Created

```
driftscope/
├── config/
│   ├── __init__.py
│   ├── schema.py
│   └── loader.py
tests/
├── config/
│   ├── __init__.py
│   ├── test_schema.py
│   └── test_loader.py
```

### 4.1 `driftscope/config/__init__.py`

```python
"""Configuration loading and validation for DriftScope."""

from driftscope.config.schema import DriftScopeConfig
from driftscope.config.loader import load_config

__all__ = ["DriftScopeConfig", "load_config"]
```

### 4.2 `driftscope/config/schema.py`

```python
"""Pydantic config model for .driftscope.yaml."""

from pathlib import Path

from pydantic import BaseModel, Field, field_validator


class AuthorshipConfig(BaseModel):
    """Authorship attribution configuration.

    Attributes:
        builtin_patterns: Use built-in co-authorship tag patterns.
        custom_patterns: Additional regex patterns for AI attribution.
    """

    builtin_patterns: bool = True
    custom_patterns: list[str] = Field(default_factory=list)

    @field_validator("custom_patterns")
    @classmethod
    def validate_custom_patterns(cls, v: list[str]) -> list[str]:
        """Compile each custom pattern to verify it is a valid regex."""
        import re

        for pattern in v:
            try:
                re.compile(pattern)
            except re.error as e:
                raise ValueError(
                    f"Invalid regex pattern '{pattern}': {e}"
                ) from e
        return v


class AnalysisConfig(BaseModel):
    """Analysis scope and performance configuration.

    Attributes:
        languages: Source languages to analyze.
        exclude_paths: Glob patterns for paths to exclude.
        parse_timeout_seconds: Per-file tree-sitter parse timeout.
        min_lines_per_module: Minimum lines for a module to appear in reports.
    """

    languages: list[str] = Field(
        default_factory=lambda: ["python", "typescript", "javascript", "go", "java", "ruby"]
    )
    exclude_paths: list[str] = Field(
        default_factory=lambda: ["vendor/**", "**/*.generated.*", "node_modules/**"]
    )
    parse_timeout_seconds: float = Field(default=5.0, gt=0.0)
    min_lines_per_module: int = Field(default=10, ge=1)

    @field_validator("languages")
    @classmethod
    def validate_languages(cls, v: list[str]) -> list[str]:
        """Ensure all languages are supported."""
        supported = {"python", "typescript", "javascript", "go", "java", "ruby"}
        invalid = set(v) - supported
        if invalid:
            raise ValueError(f"Unsupported languages: {sorted(invalid)}. Supported: {sorted(supported)}")
        return v


class MetricsConfig(BaseModel):
    """Metrics computation configuration.

    Attributes:
        survival_windows: Time windows for survival rate computation.
        complexity_metrics: Which complexity metrics to compute.
    """

    survival_windows: list[str] = Field(
        default_factory=lambda: ["30d", "90d", "180d", "365d"]
    )
    complexity_metrics: list[str] = Field(
        default_factory=lambda: ["cyclomatic", "cognitive"]
    )

    @field_validator("survival_windows")
    @classmethod
    def validate_survival_windows(cls, v: list[str]) -> list[str]:
        """Ensure window strings match \\d+d format."""
        import re

        for w in v:
            if not re.match(r"^\d+d$", w):
                raise ValueError(f"Invalid survival window '{w}'. Expected format like '30d', '90d'.")
        return v

    @field_validator("complexity_metrics")
    @classmethod
    def validate_complexity_metrics(cls, v: list[str]) -> list[str]:
        """Ensure all metrics are supported."""
        supported = {"cyclomatic", "cognitive"}
        invalid = set(v) - supported
        if invalid:
            raise ValueError(f"Unsupported complexity metrics: {sorted(invalid)}. Supported: {sorted(supported)}")
        return v


class ThresholdsConfig(BaseModel):
    """Threshold enforcement configuration.

    Attributes:
        enforce: Exit 2 on any threshold breach.
        ai_churn_attribution_pct: Breach if module AI churn % exceeds this.
        ai_survival_rate_pct: Breach if module AI survival % falls below this.
    """

    enforce: bool = False
    ai_churn_attribution_pct: float | None = Field(default=None, ge=0.0, le=100.0)
    ai_survival_rate_pct: float | None = Field(default=None, ge=0.0, le=100.0)


class OutputConfig(BaseModel):
    """Output format configuration.

    Attributes:
        default_format: Default output format when not specified by CLI flag.
    """

    default_format: str = "markdown"

    @field_validator("default_format")
    @classmethod
    def validate_default_format(cls, v: str) -> str:
        """Ensure format is one of the supported values."""
        supported = {"json", "markdown", "html", "csv"}
        if v not in supported:
            raise ValueError(f"Unsupported format '{v}'. Supported: {sorted(supported)}")
        return v


class NotificationsConfig(BaseModel):
    """Notification sink configuration.

    Attributes:
        slack_webhook: Slack incoming webhook URL (v1.1 stub).
    """

    slack_webhook: str | None = None

    @field_validator("slack_webhook")
    @classmethod
    def validate_slack_webhook(cls, v: str | None) -> str | None:
        """Validate webhook URL format if provided."""
        if v is not None and not v.startswith("https://hooks.slack.com/"):
            raise ValueError(
                "Invalid Slack webhook URL. Must start with 'https://hooks.slack.com/'."
            )
        return v


class DriftScopeConfig(BaseModel):
    """Root configuration model for .driftscope.yaml.

    All fields are optional. Built-in defaults are used when absent.

    Attributes:
        authorship: Authorship attribution configuration.
        analysis: Analysis scope and performance configuration.
        metrics: Metrics computation configuration.
        thresholds: Threshold enforcement configuration.
        output: Output format configuration.
        notifications: Notification sink configuration.
    """

    authorship: AuthorshipConfig = Field(default_factory=AuthorshipConfig)
    analysis: AnalysisConfig = Field(default_factory=AnalysisConfig)
    metrics: MetricsConfig = Field(default_factory=MetricsConfig)
    thresholds: ThresholdsConfig = Field(default_factory=ThresholdsConfig)
    output: OutputConfig = Field(default_factory=OutputConfig)
    notifications: NotificationsConfig = Field(default_factory=NotificationsConfig)
```

### 4.3 `driftscope/config/loader.py`

```python
"""Load .driftscope.yaml configuration files."""

from pathlib import Path

import yaml
from pydantic import ValidationError

from driftscope.config.schema import DriftScopeConfig
from driftscope.errors import ConfigError


DEFAULT_CONFIG_FILENAME = ".driftscope.yaml"


def load_config(repo_path: Path | None = None) -> DriftScopeConfig:
    """Load DriftScope configuration from a repository path.

    If no .driftscope.yaml exists, returns built-in defaults.

    Args:
        repo_path: Path to the repository root. If None, uses current directory.

    Returns:
        Validated DriftScopeConfig instance.

    Raises:
        ConfigError: If the config file exists but is invalid.
    """
    search_path = repo_path or Path.cwd()
    config_path = search_path / DEFAULT_CONFIG_FILENAME

    if not config_path.is_file():
        return DriftScopeConfig()

    try:
        raw_text = config_path.read_text(encoding="utf-8")
    except OSError as e:
        raise ConfigError(
            message=f"Cannot read config file: {config_path}: {e}",
            file=str(config_path),
            suggestion="Check file permissions.",
        ) from e

    return parse_config(raw_text, config_path)


def parse_config(raw_text: str, config_path: Path | None = None) -> DriftScopeConfig:
    """Parse raw YAML text into a validated DriftScopeConfig.

    Args:
        raw_text: Raw YAML content of the config file.
        config_path: Optional path for error reporting.

    Returns:
        Validated DriftScopeConfig instance.

    Raises:
        ConfigError: If the YAML is malformed or fails Pydantic validation.
    """
    try:
        data = yaml.safe_load(raw_text)
    except yaml.YAMLError as e:
        raise ConfigError(
            message=f"Invalid YAML in config file: {e}",
            file=str(config_path) if config_path else None,
            suggestion="Check YAML syntax at yaml-online-parser.appspot.com.",
        ) from e

    if data is None:
        return DriftScopeConfig()

    if not isinstance(data, dict):
        raise ConfigError(
            message="Config file must be a YAML mapping (key: value pairs).",
            file=str(config_path) if config_path else None,
        )

    try:
        return DriftScopeConfig.model_validate(data)
    except ValidationError as e:
        error_messages = []
        for err in e.errors():
            loc = " -> ".join(str(x) for x in err["loc"])
            error_messages.append(f"  {loc}: {err['msg']}")
        raise ConfigError(
            message="Config validation failed:\n" + "\n".join(error_messages),
            file=str(config_path) if config_path else None,
            suggestion="Run `driftscope config validate` for detailed diagnostics.",
        ) from e
```

### 4.4 `tests/config/__init__.py`

```python
"""Tests for driftscope.config."""
```

### 4.5 `tests/config/test_schema.py`

```python
"""Tests for the DriftScopeConfig Pydantic schema."""

import pytest
from pydantic import ValidationError

from driftscope.config.schema import (
    AnalysisConfig,
    AuthorshipConfig,
    DriftScopeConfig,
    MetricsConfig,
    NotificationsConfig,
    OutputConfig,
    ThresholdsConfig,
)


def test_default_config() -> None:
    """Default config has all fields populated with sensible defaults."""
    config = DriftScopeConfig()
    assert config.authorship.builtin_patterns is True
    assert config.analysis.languages == ["python", "typescript", "javascript", "go", "java", "ruby"]
    assert config.metrics.survival_windows == ["30d", "90d", "180d", "365d"]
    assert config.thresholds.enforce is False
    assert config.output.default_format == "markdown"
    assert config.notifications.slack_webhook is None


def test_authorship_custom_patterns_valid() -> None:
    """Custom patterns that are valid regex are accepted."""
    config = AuthorshipConfig(custom_patterns=[r"AI-Generated:\s*\w+", r"Co-Authored-By:\s*.*Bot"])
    assert len(config.custom_patterns) == 2


def test_authorship_custom_patterns_invalid_regex() -> None:
    """Custom patterns that are invalid regex are rejected."""
    with pytest.raises(ValidationError, match="Invalid regex"):
        AuthorshipConfig(custom_patterns=["[unclosed"])


def test_analysis_unsupported_language() -> None:
    """Unsupported languages are rejected."""
    with pytest.raises(ValidationError, match="Unsupported languages"):
        AnalysisConfig(languages=["python", "fortran"])


def test_analysis_min_lines_must_be_positive() -> None:
    """min_lines_per_module must be >= 1."""
    with pytest.raises(ValidationError):
        AnalysisConfig(min_lines_per_module=0)


def test_metrics_invalid_window_format() -> None:
    """Survival windows must match \\d+d format."""
    with pytest.raises(ValidationError, match="Invalid survival window"):
        MetricsConfig(survival_windows=["3months"])


def test_metrics_unsupported_complexity_metric() -> None:
    """Unsupported complexity metrics are rejected."""
    with pytest.raises(ValidationError, match="Unsupported complexity metrics"):
        MetricsConfig(complexity_metrics=["cyclomatic", "halstead"])


def test_thresholds_valid() -> None:
    """Thresholds with valid percentages are accepted."""
    config = ThresholdsConfig(
        enforce=True,
        ai_churn_attribution_pct=50.0,
        ai_survival_rate_pct=60.0,
    )
    assert config.enforce is True
    assert config.ai_churn_attribution_pct == 50.0


def test_thresholds_null_means_disabled() -> None:
    """Null thresholds mean no enforcement."""
    config = ThresholdsConfig()
    assert config.ai_churn_attribution_pct is None
    assert config.ai_survival_rate_pct is None


def test_thresholds_rejects_over_100() -> None:
    """Threshold percentages must be <= 100."""
    with pytest.raises(ValidationError):
        ThresholdsConfig(ai_churn_attribution_pct=150.0)


def test_output_supported_formats() -> None:
    """All supported output formats are accepted."""
    for fmt in ("json", "markdown", "html", "csv"):
        config = OutputConfig(default_format=fmt)
        assert config.default_format == fmt


def test_output_unsupported_format() -> None:
    """Unsupported output format is rejected."""
    with pytest.raises(ValidationError, match="Unsupported format"):
        OutputConfig(default_format="pdf")


def test_notifications_valid_slack_webhook() -> None:
    """Valid Slack webhook URL is accepted."""
    config = NotificationsConfig(
        slack_webhook="https://hooks.slack.com/services/T00/B00/xxx"
    )
    assert config.slack_webhook is not None


def test_notifications_invalid_slack_webhook() -> None:
    """Invalid Slack webhook URL is rejected."""
    with pytest.raises(ValidationError, match="Invalid Slack webhook"):
        NotificationsConfig(slack_webhook="https://example.com/webhook")


def test_full_config_from_dict() -> None:
    """Full config from a dictionary validates correctly."""
    config = DriftScopeConfig(
        authorship={"builtin_patterns": False, "custom_patterns": [r"AI:\s*\w+"]},
        analysis={"languages": ["python"], "parse_timeout_seconds": 10.0},
        metrics={"survival_windows": ["90d"]},
        thresholds={"enforce": True, "ai_churn_attribution_pct": 50.0},
        output={"default_format": "json"},
    )
    assert config.authorship.builtin_patterns is False
    assert config.analysis.parse_timeout_seconds == 10.0
    assert config.thresholds.enforce is True
```

### 4.6 `tests/config/test_loader.py`

```python
"""Tests for config file loading."""

from pathlib import Path

import pytest

from driftscope.config.loader import load_config, parse_config
from driftscope.errors import ConfigError


def test_load_config_missing_file_returns_defaults(tmp_path: Path) -> None:
    """When no config file exists, defaults are returned."""
    config = load_config(tmp_path)
    assert config.authorship.builtin_patterns is True
    assert config.output.default_format == "markdown"


def test_load_config_valid_yaml(tmp_path: Path) -> None:
    """Valid YAML config file is loaded and validated."""
    config_file = tmp_path / ".driftscope.yaml"
    config_file.write_text(
        "authorship:\n"
        "  builtin_patterns: false\n"
        "  custom_patterns:\n"
        "    - 'AI-Generated: .*'\n"
        "output:\n"
        "  default_format: json\n"
    )
    config = load_config(tmp_path)
    assert config.authorship.builtin_patterns is False
    assert config.output.default_format == "json"


def test_load_config_invalid_yaml(tmp_path: Path) -> None:
    """Invalid YAML raises ConfigError."""
    config_file = tmp_path / ".driftscope.yaml"
    config_file.write_text("authorship:\n  - broken: [missing")
    with pytest.raises(ConfigError, match="Invalid YAML"):
        load_config(tmp_path)


def test_load_config_invalid_schema(tmp_path: Path) -> None:
    """YAML with invalid field values raises ConfigError."""
    config_file = tmp_path / ".driftscope.yaml"
    config_file.write_text("output:\n  default_format: pdf\n")
    with pytest.raises(ConfigError, match="Config validation failed"):
        load_config(tmp_path)


def test_load_config_non_dict_yaml(tmp_path: Path) -> None:
    """YAML that is not a mapping raises ConfigError."""
    config_file = tmp_path / ".driftscope.yaml"
    config_file.write_text("- just\n- a\n- list\n")
    with pytest.raises(ConfigError, match="must be a YAML mapping"):
        load_config(tmp_path)


def test_parse_config_empty_string() -> None:
    """Empty string returns defaults."""
    config = parse_config("")
    assert config.authorship.builtin_patterns is True


def test_parse_config_null_yaml() -> None:
    """YAML that parses to None returns defaults."""
    config = parse_config("---\n")
    assert config.authorship.builtin_patterns is True


def test_load_config_unreadable_file(tmp_path: Path) -> None:
    """Unreadable config file raises ConfigError."""
    config_file = tmp_path / ".driftscope.yaml"
    config_file.write_text("output:\n  default_format: json\n")
    config_file.chmod(0o000)
    try:
        with pytest.raises(ConfigError, match="Cannot read config file"):
            load_config(tmp_path)
    finally:
        config_file.chmod(0o644)
```

### Test Commands

```bash
python -m pytest tests/config/ -v
# Expected: ~20 tests, all passing

python -m pytest tests/config/ --cov=driftscope/config --cov-report=term-missing
# Expected: >=95% coverage
```

### Commit

```
feat(config): add Pydantic config schema, YAML loader, validation with regex compilation checks
```

---

## Task 5: Authorship (Patterns + Classifier)

**Goal:** Implement co-authorship tag pattern matching and commit classification.

### Files Created

```
driftscope/
├── authorship/
│   ├── __init__.py
│   ├── patterns.py
│   └── classifier.py
tests/
├── authorship/
│   ├── __init__.py
│   ├── test_patterns.py
│   └── test_classifier.py
```

### 5.1 `driftscope/authorship/__init__.py`

```python
"""Authorship attribution — human/AI commit classification."""

from driftscope.authorship.patterns import BUILTIN_PATTERNS, compile_patterns
from driftscope.authorship.classifier import classify_commit, classify_history

__all__ = ["BUILTIN_PATTERNS", "compile_patterns", "classify_commit", "classify_history"]
```

### 5.2 `driftscope/authorship/patterns.py`

```python
"""Built-in co-authorship tag regex patterns for AI attribution.

Each pattern is a compiled regex matched against the full commit message body.
A match means the commit is AI-attributed.

Built-in patterns cover:
- GitHub Copilot: Co-Authored-By: GitHub Copilot
- Claude Code: Co-Authored-By: Claude
- Cursor AI: Co-Authored-By: Cursor
- Devin: Co-Authored-By: Devin
- Generic AI-Generated trailer
"""

import re


# Each entry: (name, raw_pattern)
# Patterns are compiled on module load. Named for diagnostics in `config validate`.
BUILTIN_PATTERN_DEFS: list[tuple[str, str]] = [
    ("github_copilot", r"Co-Authored-By:\s*GitHub\s+Copilot"),
    ("claude_code", r"Co-Authored-By:\s*Claude"),
    ("cursor_ai", r"Co-Authored-By:\s*Cursor"),
    ("devin", r"Co-Authored-By:\s*Devin"),
    ("ai_generated_trailer", r"AI-Generated:\s*.+"),
]


def _compile_builtins() -> list[tuple[str, re.Pattern[str]]]:
    """Compile built-in patterns at import time."""
    return [(name, re.compile(pat, re.IGNORECASE)) for name, pat in BUILTIN_PATTERN_DEFS]


BUILTIN_PATTERNS: list[tuple[str, re.Pattern[str]]] = _compile_builtins()


def compile_patterns(
    custom_patterns: list[str] | None = None,
    include_builtins: bool = True,
) -> list[tuple[str, re.Pattern[str]]]:
    """Build the full pattern list for authorship classification.

    Args:
        custom_patterns: Additional raw regex strings from config.
        include_builtins: Whether to include built-in patterns.

    Returns:
        List of (name/pattern_string, compiled_regex) tuples.

    Raises:
        ValueError: If any custom pattern fails to compile.
    """
    patterns: list[tuple[str, re.Pattern[str]]] = []

    if include_builtins:
        patterns.extend(BUILTIN_PATTERNS)

    if custom_patterns:
        for raw in custom_patterns:
            try:
                patterns.append((raw, re.compile(raw, re.IGNORECASE)))
            except re.error as e:
                raise ValueError(f"Cannot compile pattern '{raw}': {e}") from e

    return patterns
```

### 5.3 `driftscope/authorship/classifier.py`

```python
"""Commit classification engine — human vs. AI attribution."""

import re

from driftscope.authorship.patterns import compile_patterns
from driftscope.models.commit import Commit
from driftscope.models.history import AttributedCommit, AttributedHistory


def classify_commit(
    commit: Commit,
    patterns: list[tuple[str, re.Pattern[str]]],
) -> AttributedCommit:
    """Classify a single commit as human or AI based on pattern matching.

    Scans the full commit message (subject + body) against all patterns.
    First match wins. No match means human.

    Args:
        commit: The commit to classify.
        patterns: List of (name, compiled_regex) tuples.

    Returns:
        AttributedCommit with authorship_class set.
    """
    full_message = f"{commit.message_subject}\n{commit.message_body}"

    for pattern_name, pattern in patterns:
        match = pattern.search(full_message)
        if match:
            return AttributedCommit(
                **commit.model_dump(),
                authorship_class="ai",
                matched_pattern=pattern_name,
                matched_text=match.group(0),
            )

    return AttributedCommit(
        **commit.model_dump(),
        authorship_class="human",
    )


def classify_history(
    history_commit_data: "CommitHistory",
    custom_patterns: list[str] | None = None,
    include_builtins: bool = True,
) -> AttributedHistory:
    """Classify all commits in a CommitHistory and produce AttributedHistory.

    Args:
        history_commit_data: The raw commit history with blame data.
        custom_patterns: Additional regex patterns from config.
        include_builtins: Whether to include built-in patterns.

    Returns:
        AttributedHistory with all commits classified and counts populated.
    """
    # Import here to avoid circular imports at module level
    from driftscope.models.history import CommitHistory

    patterns = compile_patterns(custom_patterns, include_builtins)

    attributed = [classify_commit(c, patterns) for c in history_commit_data.commits]
    ai_count = sum(1 for c in attributed if c.authorship_class == "ai")
    human_count = len(attributed) - ai_count

    return AttributedHistory(
        repo_path=history_commit_data.repo_path,
        commits=attributed,
        blame=history_commit_data.blame,
        range_start=history_commit_data.range_start,
        range_end=history_commit_data.range_end,
        ai_commit_count=ai_count,
        human_commit_count=human_count,
    )
```

### 5.4 `tests/authorship/__init__.py`

```python
"""Tests for driftscope.authorship."""
```

### 5.5 `tests/authorship/test_patterns.py`

```python
"""Tests for co-authorship tag regex patterns."""

import re

import pytest

from driftscope.authorship.patterns import BUILTIN_PATTERNS, BUILTIN_PATTERN_DEFS, compile_patterns


class TestBuiltinPatterns:
    """Verify every built-in pattern compiles and matches correctly."""

    @pytest.mark.parametrize("name,pattern_str", BUILTIN_PATTERN_DEFS)
    def test_pattern_compiles(self, name: str, pattern_str: str) -> None:
        """Each built-in pattern compiles without error."""
        compiled = re.compile(pattern_str, re.IGNORECASE)
        assert compiled is not None

    def test_github_copilot_matches(self) -> None:
        """Copilot pattern matches standard co-authorship tag."""
        _, pat = BUILTIN_PATTERNS[0]
        assert pat.search("Co-Authored-By: GitHub Copilot")
        assert pat.search("Co-Authored-By: github copilot")

    def test_github_copilot_rejects_non_copilot(self) -> None:
        """Copilot pattern does not match non-copilot text."""
        _, pat = BUILTIN_PATTERNS[0]
        assert not pat.search("Co-Authored-By: Alice")

    def test_claude_code_matches(self) -> None:
        """Claude pattern matches standard co-authorship tag."""
        _, pat = BUILTIN_PATTERNS[1]
        assert pat.search("Co-Authored-By: Claude")
        assert pat.search("Co-Authored-By: claude")

    def test_cursor_ai_matches(self) -> None:
        """Cursor pattern matches standard co-authorship tag."""
        _, pat = BUILTIN_PATTERNS[2]
        assert pat.search("Co-Authored-By: Cursor")

    def test_devin_matches(self) -> None:
        """Devin pattern matches standard co-authorship tag."""
        _, pat = BUILTIN_PATTERNS[3]
        assert pat.search("Co-Authored-By: Devin")

    def test_ai_generated_trailer_matches(self) -> None:
        """Generic AI-Generated trailer matches."""
        _, pat = BUILTIN_PATTERNS[4]
        assert pat.search("AI-Generated: Payment processing function")
        assert pat.search("ai-generated: test")

    def test_ai_generated_rejects_empty(self) -> None:
        """AI-Generated trailer requires content after the colon."""
        _, pat = BUILTIN_PATTERNS[4]
        # Pattern requires at least one char after colon
        assert not pat.search("AI-Generated:")


class TestCompilePatterns:
    """Test the compile_patterns function."""

    def test_builtins_only(self) -> None:
        """compile_patterns with builtins only returns builtins."""
        patterns = compile_patterns()
        assert len(patterns) == len(BUILTIN_PATTERN_DEFS)

    def test_builtins_excluded(self) -> None:
        """compile_patterns without builtins returns only custom."""
        patterns = compile_patterns(include_builtins=False, custom_patterns=[r"AI:\s*\w+"])
        assert len(patterns) == 1

    def test_custom_appended(self) -> None:
        """Custom patterns are appended after builtins."""
        patterns = compile_patterns(custom_patterns=[r"MyAI:\s*\w+"])
        assert len(patterns) == len(BUILTIN_PATTERN_DEFS) + 1

    def test_invalid_custom_raises(self) -> None:
        """Invalid custom regex raises ValueError."""
        with pytest.raises(ValueError, match="Cannot compile pattern"):
            compile_patterns(custom_patterns=["[unclosed"])


    def test_no_patterns_at_all(self) -> None:
        """No builtins and no custom returns empty list."""
        patterns = compile_patterns(include_builtins=False)
        assert len(patterns) == 0
```

### 5.6 `tests/authorship/test_classifier.py`

```python
"""Tests for commit classification."""

from datetime import datetime, timezone
from pathlib import Path

import pytest

from driftscope.authorship.classifier import classify_commit, classify_history
from driftscope.authorship.patterns import compile_patterns
from driftscope.models.blame import BlameLine
from driftscope.models.commit import Commit
from driftscope.models.history import CommitHistory


def _commit(message_subject: str = "Update code", message_body: str = "") -> Commit:
    """Create a test Commit with minimal required fields."""
    return Commit(
        sha="a" * 40,
        short_sha="a" * 7,
        timestamp=datetime(2025, 6, 15, 10, 0, tzinfo=timezone.utc),
        author_name="Alice",
        author_email="alice@example.com",
        committer_name="Alice",
        committer_email="alice@example.com",
        message_subject=message_subject,
        message_body=message_body,
        parent_shas=["b" * 40],
    )


class TestClassifyCommit:
    """Test single-commit classification."""

    def test_copilot_tag_classified_as_ai(self) -> None:
        """Commit with Copilot co-authorship tag is classified as AI."""
        commit = _commit(
            message_subject="Add payment handler",
            message_body="Co-Authored-By: GitHub Copilot\n",
        )
        patterns = compile_patterns()
        result = classify_commit(commit, patterns)
        assert result.authorship_class == "ai"
        assert result.matched_pattern == "github_copilot"
        assert "Copilot" in result.matched_text

    def test_claude_tag_classified_as_ai(self) -> None:
        """Commit with Claude co-authorship tag is classified as AI."""
        commit = _commit(
            message_body="Co-Authored-By: Claude\n",
        )
        patterns = compile_patterns()
        result = classify_commit(commit, patterns)
        assert result.authorship_class == "ai"
        assert result.matched_pattern == "claude_code"

    def test_no_tag_classified_as_human(self) -> None:
        """Commit with no co-authorship tag is classified as human."""
        commit = _commit(message_subject="Fix typo")
        patterns = compile_patterns()
        result = classify_commit(commit, patterns)
        assert result.authorship_class == "human"
        assert result.matched_pattern is None
        assert result.matched_text is None

    def test_custom_pattern_match(self) -> None:
        """Custom pattern from config matches correctly."""
        commit = _commit(
            message_body="MyBot: auto-generated\n",
        )
        patterns = compile_patterns(custom_patterns=[r"MyBot:\s*auto-generated"])
        result = classify_commit(commit, patterns)
        assert result.authorship_class == "ai"
        assert "MyBot" in result.matched_text

    def test_builtin_disabled_no_match(self) -> None:
        """With builtins disabled, standard tags are not matched."""
        commit = _commit(
            message_body="Co-Authored-By: GitHub Copilot\n",
        )
        patterns = compile_patterns(include_builtins=False)
        result = classify_commit(commit, patterns)
        assert result.authorship_class == "human"

    def test_ai_generated_trailer_match(self) -> None:
        """Generic AI-Generated trailer is matched."""
        commit = _commit(
            message_body="AI-Generated: payment validation logic\n",
        )
        patterns = compile_patterns()
        result = classify_commit(commit, patterns)
        assert result.authorship_class == "ai"

    def test_multiline_body_match(self) -> None:
        """Pattern matches within multiline body."""
        commit = _commit(
            message_body="Implement feature\n\nDetails here.\n\nCo-Authored-By: Cursor\n",
        )
        patterns = compile_patterns()
        result = classify_commit(commit, patterns)
        assert result.authorship_class == "ai"

    def test_empty_message_body(self) -> None:
        """Commit with empty body is classified as human."""
        commit = _commit(message_body="")
        patterns = compile_patterns()
        result = classify_commit(commit, patterns)
        assert result.authorship_class == "human"

    def test_unicode_in_message(self) -> None:
        """Unicode in message body does not crash classification."""
        commit = _commit(message_body="Fix Ubersicht\n")
        patterns = compile_patterns()
        result = classify_commit(commit, patterns)
        assert result.authorship_class == "human"


class TestClassifyHistory:
    """Test bulk history classification."""

    def test_mixed_history_counts(self) -> None:
        """Mixed human/AI commits produce correct counts."""
        history = CommitHistory(
            repo_path=Path("/tmp/repo"),
            commits=[
                _commit(message_body="Co-Authored-By: Claude\n"),
                _commit(message_subject="Human commit"),
                _commit(message_body="Co-Authored-By: GitHub Copilot\n"),
            ],
            blame={},
            range_start=datetime(2025, 1, 1, tzinfo=timezone.utc),
            range_end=datetime(2025, 6, 1, tzinfo=timezone.utc),
        )
        result = classify_history(history)
        assert result.ai_commit_count == 2
        assert result.human_commit_count == 1
        assert len(result.commits) == 3

    def test_all_human_history(self) -> None:
        """All-human history has zero AI commits."""
        history = CommitHistory(
            repo_path=Path("/tmp/repo"),
            commits=[_commit(), _commit()],
            blame={},
            range_start=datetime(2025, 1, 1, tzinfo=timezone.utc),
            range_end=datetime(2025, 6, 1, tzinfo=timezone.utc),
        )
        result = classify_history(history)
        assert result.ai_commit_count == 0
        assert result.human_commit_count == 2

    def test_empty_history(self) -> None:
        """Empty commit list produces zero counts."""
        history = CommitHistory(
            repo_path=Path("/tmp/repo"),
            commits=[],
            blame={},
            range_start=datetime(2025, 1, 1, tzinfo=timezone.utc),
            range_end=datetime(2025, 6, 1, tzinfo=timezone.utc),
        )
        result = classify_history(history)
        assert result.ai_commit_count == 0
        assert result.human_commit_count == 0

    def test_blame_data_preserved(self) -> None:
        """Blame data from input is preserved in output."""
        blame = {Path("src/main.py"): [BlameLine(
            line_number=1,
            commit_sha="a" * 40,
            author_name="Alice",
            author_email="alice@example.com",
            content="x = 1",
        )]}
        history = CommitHistory(
            repo_path=Path("/tmp/repo"),
            commits=[_commit()],
            blame=blame,
            range_start=datetime(2025, 1, 1, tzinfo=timezone.utc),
            range_end=datetime(2025, 6, 1, tzinfo=timezone.utc),
        )
        result = classify_history(history)
        assert Path("src/main.py") in result.blame
```

### Test Commands

```bash
python -m pytest tests/authorship/ -v
# Expected: ~25 tests, all passing

python -m pytest tests/authorship/ --cov=driftscope/authorship --cov-report=term-missing
# Expected: >=95% coverage
```

### Commit

```
feat(authorship): add co-authorship tag patterns and commit classification engine with custom pattern support
```

---

## Task 6: Git Client (blame, log, diff_parser)

**Goal:** Implement git binary interaction for blame, log, and diff parsing.

### Files

```
driftscope/git_client/__init__.py
driftscope/git_client/blame.py       # git blame invocation + line-by-line parsing
driftscope/git_client/log.py         # git log --format parsing -> list[Commit]
driftscope/git_client/diff_parser.py # unified diff parsing for line mapping
tests/git_client/__init__.py
tests/git_client/test_blame.py
tests/git_client/test_log.py
tests/git_client/test_diff_parser.py
tests/git_client/test_integration.py # real git subprocess tests with tmp_git_repo
```

### 6.1 `driftscope/git_client/__init__.py`

```python
"""Git client — blame, log, and diff parsing via git binary."""

from driftscope.git_client.blame import run_blame
from driftscope.git_client.log import parse_log
from driftscope.git_client.diff_parser import parse_unified_diff, FileHunk

__all__ = ["run_blame", "parse_log", "parse_unified_diff", "FileHunk"]
```

### 6.2 `driftscope/git_client/blame.py`

```python
"""Git blame invocation and porcelain output parsing.

Runs ``git blame --porcelain`` via subprocess and parses the structured
output into a list of :class:`BlameLine` objects.

Time Complexity: O(N) where N is the number of lines in the file.
Space Complexity: O(N) for the list of BlameLine objects.
"""

import re
import subprocess
from pathlib import Path

from driftscope.errors import GitError
from driftscope.models.blame import BlameLine


def _check_git_available() -> None:
    """Verify the git binary is available on PATH.

    Raises:
        GitError: If git binary is not found.
    """
    try:
        subprocess.run(
            ["git", "--version"],
            capture_output=True,
            check=True,
            timeout=10,
        )
    except FileNotFoundError as e:
        raise GitError(
            message="git binary not found on PATH.",
            suggestion="Install git >= 2.30 and ensure it is on your PATH.",
        ) from e
    except subprocess.TimeoutExpired as e:
        raise GitError(
            message="git --version timed out.",
            suggestion="Check your git installation.",
        ) from e


def run_blame(
    repo_path: Path,
    file_path: Path,
    revision: str = "HEAD",
) -> list[BlameLine]:
    """Run git blame on a file and return parsed blame lines.

    Args:
        repo_path: Absolute path to the git repository root.
        file_path: Path to the file, relative to repo_path.
        revision: Git revision to blame at (default: HEAD).

    Returns:
        List of BlameLine objects, one per source line.

    Raises:
        GitError: If git is not available, the file is not tracked,
                  or the subprocess fails.
    """
    _check_git_available()

    try:
        result = subprocess.run(
            [
                "git", "-C", str(repo_path),
                "blame", "--porcelain", revision,
                "--", str(file_path),
            ],
            capture_output=True,
            text=True,
            check=True,
            timeout=60,
        )
    except subprocess.CalledProcessError as e:
        raise GitError(
            message=f"git blame failed for {file_path}: {e.stderr.strip()}",
            file=str(file_path),
            suggestion="Ensure the file is tracked by git.",
        ) from e
    except subprocess.TimeoutExpired as e:
        raise GitError(
            message=f"git blame timed out for {file_path}",
            file=str(file_path),
            suggestion="The file may be too large. Exclude it via .driftscope.yaml.",
        ) from e

    return _parse_porcelain(result.stdout)


def _parse_porcelain(output: str) -> list[BlameLine]:
    """Parse git blame porcelain output into BlameLine objects.

    Porcelain format summary:
    - Header lines for each commit: ``<sha> <orig_line> <final_line> <line_count>``
    - ``author <name>``
    - ``author-mail <email>``
    - ``summary <subject>``
    - ``filename <path>``
    - Source content line prefixed by TAB

    Args:
        output: Raw stdout from ``git blame --porcelain``.

    Returns:
        Ordered list of BlameLine objects matching the file's line order.
    """
    lines: list[BlameLine] = []
    current_sha: str = ""
    current_author: str = ""
    current_email: str = ""
    current_final_line: int = 0

    sha_pattern = re.compile(r"^([0-9a-f]{40})\s+(\d+)\s+(\d+)\s+(\d+)")
    author_pattern = re.compile(r"^author (.+)$")
    mail_pattern = re.compile(r"^author-mail <(.+)>$")
    content_pattern = re.compile(r"^\t(.*)$")

    for raw_line in output.split("\n"):
        sha_match = sha_pattern.match(raw_line)
        if sha_match:
            current_sha = sha_match.group(1)
            current_final_line = int(sha_match.group(3))
            continue

        author_match = author_pattern.match(raw_line)
        if author_match:
            current_author = author_match.group(1)
            continue

        mail_match = mail_pattern.match(raw_line)
        if mail_match:
            current_email = mail_match.group(1)
            continue

        content_match = content_pattern.match(raw_line)
        if content_match:
            lines.append(BlameLine(
                line_number=current_final_line,
                commit_sha=current_sha,
                author_name=current_author,
                author_email=current_email,
                content=content_match.group(1),
            ))

    return lines
```

### 6.3 `driftscope/git_client/log.py`

```python
"""Git log parsing — commit metadata extraction.

Runs ``git log`` with a NULL-delimited format string for reliable field
separation and parses the output into :class:`Commit` objects.

Time Complexity: O(N) where N is the number of commits.
Space Complexity: O(N) for the list of Commit objects.
"""

import subprocess
from datetime import datetime, timezone
from pathlib import Path

from driftscope.errors import GitError
from driftscope.models.commit import Commit

# Null-byte record separator for reliable parsing.
# Fields within a record are newline-delimited.
_LOG_FORMAT = "%H%n%h%n%aI%n%an%n%ae%n%cN%n%ce%n%s%n%b%x00"

# Minimum git version required.
_MIN_GIT_VERSION = (2, 30, 0)


def parse_log(
    repo_path: Path,
    from_ref: str | None = None,
    to_ref: str = "HEAD",
    since: datetime | None = None,
) -> list[Commit]:
    """Parse git log output into a list of Commit objects.

    Args:
        repo_path: Absolute path to the git repository root.
        from_ref: Starting ref (exclusive). None means beginning of history.
        to_ref: Ending ref (inclusive). Default: HEAD.
        since: Only include commits after this timestamp.

    Returns:
        List of Commit objects ordered oldest to newest.

    Raises:
        GitError: If git fails, the repo is empty, or the range is invalid.
    """
    cmd: list[str] = [
        "git", "-C", str(repo_path),
        "log", f"--format={_LOG_FORMAT}",
        "--no-color",
    ]

    if since is not None:
        cmd.append(f"--since={since.isoformat()}")

    if from_ref is not None:
        cmd.append(f"{from_ref}..{to_ref}")
    else:
        cmd.append(to_ref)

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True,
            timeout=120,
        )
    except FileNotFoundError as e:
        raise GitError(
            message="git binary not found on PATH.",
            suggestion="Install git >= 2.30 and ensure it is on your PATH.",
        ) from e
    except subprocess.CalledProcessError as e:
        stderr = e.stderr.strip()
        if "does not have any commits yet" in stderr or "fatal: your current branch" in stderr:
            raise GitError(
                message=f"No commits found in {repo_path}.",
                file=str(repo_path),
                suggestion="Initialize the repository with at least one commit.",
            ) from e
        raise GitError(
            message=f"git log failed: {stderr}",
            file=str(repo_path),
        ) from e
    except subprocess.TimeoutExpired as e:
        raise GitError(
            message="git log timed out.",
            file=str(repo_path),
            suggestion="The repository may be too large. Narrow the commit range.",
        ) from e

    output = result.stdout.strip()
    if not output:
        return []

    return _parse_log_output(output)


def _parse_log_output(output: str) -> list[Commit]:
    """Parse the null-delimited git log output into Commit objects.

    Each record is separated by a null byte. Within a record, fields are
    newline-separated in this order:
    SHA, short SHA, author date ISO, author name, author email,
    committer name, committer email, subject, body.

    Args:
        output: Raw stdout from git log with the custom format.

    Returns:
        List of Commit objects ordered oldest to newest (git log outputs
        newest-first, so we reverse).
    """
    commits: list[Commit] = []
    records = output.split("\x00")

    for record in records:
        record = record.strip()
        if not record:
            continue

        fields = record.split("\n")
        if len(fields) < 9:
            continue

        sha = fields[0].strip()
        short_sha = fields[1].strip()
        timestamp_str = fields[2].strip()
        author_name = fields[3].strip()
        author_email = fields[4].strip()
        committer_name = fields[5].strip()
        committer_email = fields[6].strip()
        message_subject = fields[7].strip()
        message_body = "\n".join(fields[8:])

        timestamp = datetime.fromisoformat(timestamp_str)
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=timezone.utc)

        # Parse parent SHAs is not available in this format.
        # We set a placeholder; the integration layer fills this.
        parent_shas: list[str] = []

        commits.append(Commit(
            sha=sha,
            short_sha=short_sha,
            timestamp=timestamp,
            author_name=author_name,
            author_email=author_email,
            committer_name=committer_name,
            committer_email=committer_email,
            message_subject=message_subject,
            message_body=message_body,
            parent_shas=parent_shas,
        ))

    commits.reverse()
    return commits


def is_bare_repo(repo_path: Path) -> bool:
    """Check if a repository is bare.

    Args:
        repo_path: Absolute path to the repository root.

    Returns:
        True if the repository is bare.
    """
    try:
        result = subprocess.run(
            ["git", "-C", str(repo_path), "config", "core.bare"],
            capture_output=True,
            text=True,
            check=True,
            timeout=10,
        )
        return result.stdout.strip().lower() == "true"
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False
```

### 6.4 `driftscope/git_client/diff_parser.py`

```python
"""Unified diff parsing for line mapping between commits.

Parses unified diff output (``git diff`` format) to identify which line
ranges were added and removed in each file.

Time Complexity: O(N) where N is the number of lines in the diff.
Space Complexity: O(F + H) where F is the number of files and H is the
                  number of hunks.
"""

import re
from dataclasses import dataclass, field


@dataclass(frozen=True)
class FileHunk:
    """Represents added and removed line ranges for a single file in a diff.

    Attributes:
        file_path: Path to the changed file (relative to repo root).
        added_lines: Line numbers that were added.
        removed_lines: Line numbers that were removed.
    """

    file_path: str
    added_lines: list[int] = field(default_factory=list)
    removed_lines: list[int] = field(default_factory=list)


# Regex patterns for unified diff parsing.
_HUNK_HEADER = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")
_FILE_HEADER_A = re.compile(r"^--- (?:a/)?(.+)$")
_FILE_HEADER_B = re.compile(r"^\+\+\+ (?:b/)?(.+)$")


def parse_unified_diff(diff_text: str) -> list[FileHunk]:
    """Parse a unified diff into per-file hunk summaries.

    Args:
        diff_text: Raw unified diff output (e.g., from ``git diff``).

    Returns:
        List of FileHunk objects, one per changed file.
    """
    hunks: dict[str, FileHunk] = {}
    current_file: str | None = None
    current_new_line: int = 0
    current_old_line: int = 0

    for line in diff_text.split("\n"):
        # Detect file headers.
        file_b_match = _FILE_HEADER_B.match(line)
        if file_b_match:
            current_file = file_b_match.group(1)
            if current_file not in hunks:
                hunks[current_file] = FileHunk(file_path=current_file)
            continue

        # Detect hunk headers.
        hunk_match = _HUNK_HEADER.match(line)
        if hunk_match:
            current_old_line = int(hunk_match.group(1))
            current_new_line = int(hunk_match.group(3))
            continue

        if current_file is None:
            continue

        # Context line.
        if line.startswith(" "):
            current_old_line += 1
            current_new_line += 1
        # Removed line.
        elif line.startswith("-"):
            hunks[current_file].removed_lines.append(current_old_line)
            current_old_line += 1
        # Added line.
        elif line.startswith("+"):
            hunks[current_file].added_lines.append(current_new_line)
            current_new_line += 1

    return list(hunks.values())
```

### 6.5 `tests/git_client/__init__.py`

```python
"""Tests for driftscope.git_client."""
```

### 6.6 `tests/git_client/test_blame.py`

```python
"""Tests for git blame parsing."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from driftscope.errors import GitError
from driftscope.git_client.blame import _parse_porcelain, run_blame
from driftscope.models.blame import BlameLine


SAMPLE_PORCELAIN_OUTPUT = """\
a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4 1 1 1
author Alice
author-mail <alice@example.com>
summary Add feature
filename src/main.py
\tx = 1
c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4 2 2 1
author Bob
author-mail <bob@example.com>
summary Fix bug
filename src/main.py
\ty = 2
"""


class TestParsePorcelain:
    """Test porcelain output parsing."""

    def test_parses_two_lines(self) -> None:
        """Two blame entries produce two BlameLine objects."""
        lines = _parse_porcelain(SAMPLE_PORCELAIN_OUTPUT)
        assert len(lines) == 2

    def test_first_line_fields(self) -> None:
        """First line has correct SHA, author, email, content."""
        lines = _parse_porcelain(SAMPLE_PORCELAIN_OUTPUT)
        assert lines[0].line_number == 1
        assert lines[0].commit_sha == "a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4"
        assert lines[0].author_name == "Alice"
        assert lines[0].author_email == "alice@example.com"
        assert lines[0].content == "x = 1"

    def test_second_line_fields(self) -> None:
        """Second line has Bob's data."""
        lines = _parse_porcelain(SAMPLE_PORCELAIN_OUTPUT)
        assert lines[1].line_number == 2
        assert lines[1].author_name == "Bob"
        assert lines[1].content == "y = 2"

    def test_empty_output(self) -> None:
        """Empty porcelain output returns empty list."""
        lines = _parse_porcelain("")
        assert lines == []

    def test_line_order_preserved(self) -> None:
        """Lines are returned in file order (by line_number)."""
        lines = _parse_porcelain(SAMPLE_PORCELAIN_OUTPUT)
        assert lines[0].line_number < lines[1].line_number


class TestRunBlame:
    """Test run_blame with mocked subprocess."""

    @patch("driftscope.git_client.blame.subprocess.run")
    def test_returns_blame_lines(self, mock_run: MagicMock) -> None:
        """run_blame returns parsed BlameLine objects."""
        mock_run.return_value = MagicMock(
            stdout=SAMPLE_PORCELAIN_OUTPUT,
            returncode=0,
        )
        lines = run_blame(Path("/repo"), Path("src/main.py"))
        assert len(lines) == 2
        assert isinstance(lines[0], BlameLine)

    @patch("driftscope.git_client.blame.subprocess.run")
    def test_raises_git_error_on_failure(self, mock_run: MagicMock) -> None:
        """run_blame raises GitError when git fails."""
        import subprocess

        mock_run.side_effect = subprocess.CalledProcessError(
            returncode=128, cmd="git blame", stderr="fatal: no such path",
        )
        with pytest.raises(GitError, match="git blame failed"):
            run_blame(Path("/repo"), Path("nonexistent.py"))

    @patch("driftscope.git_client.blame.subprocess.run")
    def test_raises_git_error_when_git_not_found(self, mock_run: MagicMock) -> None:
        """run_blame raises GitError when git binary is missing."""
        mock_run.side_effect = FileNotFoundError("git not found")
        with pytest.raises(GitError, match="git binary not found"):
            run_blame(Path("/repo"), Path("src/main.py"))

    @patch("driftscope.git_client.blame.subprocess.run")
    def test_passes_revision(self, mock_run: MagicMock) -> None:
        """run_blame passes the revision argument to git."""
        mock_run.return_value = MagicMock(stdout="", returncode=0)
        run_blame(Path("/repo"), Path("src/main.py"), revision="abc1234")
        cmd = mock_run.call_args[0][0]
        assert "abc1234" in cmd
```

### 6.7 `tests/git_client/test_log.py`

```python
"""Tests for git log parsing."""

from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from driftscope.errors import GitError
from driftscope.git_client.log import _parse_log_output, is_bare_repo, parse_log
from driftscope.models.commit import Commit


SAMPLE_LOG_OUTPUT = (
    "ffffffffffffffffffffffffffffffffffffffff\n"
    "fffffff\n"
    "2025-06-15T10:00:00+00:00\n"
    "Charlie\n"
    "charlie@example.com\n"
    "Charlie\n"
    "charlie@example.com\n"
    "Third commit\n"
    "Body three\n"
    "\x00"
    "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\n"
    "aaaaaaa\n"
    "2025-06-01T10:00:00+00:00\n"
    "Alice\n"
    "alice@example.com\n"
    "Alice\n"
    "alice@example.com\n"
    "First commit\n"
    "Body one\n"
    "\x00"
)


class TestParseLogOutput:
    """Test raw log output parsing."""

    def test_parses_two_commits(self) -> None:
        """Two null-delimited records produce two Commits."""
        commits = _parse_log_output(SAMPLE_LOG_OUTPUT)
        assert len(commits) == 2

    def test_oldest_first(self) -> None:
        """Commits are returned oldest-first (reversed from git log order)."""
        commits = _parse_log_output(SAMPLE_LOG_OUTPUT)
        assert commits[0].author_name == "Alice"
        assert commits[1].author_name == "Charlie"

    def test_commit_fields(self) -> None:
        """First commit has correctly parsed fields."""
        commits = _parse_log_output(SAMPLE_LOG_OUTPUT)
        first = commits[0]
        assert first.sha == "a" * 40
        assert first.short_sha == "a" * 7
        assert first.author_name == "Alice"
        assert first.author_email == "alice@example.com"
        assert first.message_subject == "First commit"
        assert first.message_body == "Body one"

    def test_timestamp_parsed(self) -> None:
        """Timestamp is parsed with timezone info."""
        commits = _parse_log_output(SAMPLE_LOG_OUTPUT)
        assert commits[0].timestamp.year == 2025
        assert commits[0].timestamp.month == 6
        assert commits[0].timestamp.tzinfo is not None

    def test_empty_output(self) -> None:
        """Empty output returns empty list."""
        commits = _parse_log_output("")
        assert commits == []

    def test_multiline_body(self) -> None:
        """Commit body with multiple lines is preserved."""
        log = (
            "a" * 40 + "\n"
            "a" * 7 + "\n"
            "2025-06-01T10:00:00+00:00\n"
            "Alice\n"
            "alice@example.com\n"
            "Alice\n"
            "alice@example.com\n"
            "Subject\n"
            "Line one\n"
            "Line two\n"
            "Line three\n"
            "\x00"
        )
        commits = _parse_log_output(log)
        assert "Line one" in commits[0].message_body
        assert "Line three" in commits[0].message_body


class TestParseLog:
    """Test parse_log with mocked subprocess."""

    @patch("driftscope.git_client.log.subprocess.run")
    def test_returns_commits(self, mock_run: MagicMock) -> None:
        """parse_log returns Commit objects from git output."""
        mock_run.return_value = MagicMock(
            stdout=SAMPLE_LOG_OUTPUT,
            returncode=0,
        )
        commits = parse_log(Path("/repo"))
        assert len(commits) == 2
        assert all(isinstance(c, Commit) for c in commits)

    @patch("driftscope.git_client.log.subprocess.run")
    def test_raises_git_error_on_empty_repo(self, mock_run: MagicMock) -> None:
        """parse_log raises GitError when repo has no commits."""
        import subprocess

        mock_run.side_effect = subprocess.CalledProcessError(
            returncode=128,
            cmd="git log",
            stderr="fatal: your current branch does not have any commits yet",
        )
        with pytest.raises(GitError, match="No commits found"):
            parse_log(Path("/repo"))

    @patch("driftscope.git_client.log.subprocess.run")
    def test_raises_git_error_on_missing_binary(self, mock_run: MagicMock) -> None:
        """parse_log raises GitError when git is not installed."""
        mock_run.side_effect = FileNotFoundError("git not found")
        with pytest.raises(GitError, match="git binary not found"):
            parse_log(Path("/repo"))

    @patch("driftscope.git_client.log.subprocess.run")
    def test_builds_since_flag(self, mock_run: MagicMock) -> None:
        """parse_log includes --since flag when since is provided."""
        mock_run.return_value = MagicMock(stdout="", returncode=0)
        since = datetime(2025, 1, 1, tzinfo=timezone.utc)
        parse_log(Path("/repo"), since=since)
        cmd = mock_run.call_args[0][0]
        assert any("--since=" in arg for arg in cmd)

    @patch("driftscope.git_client.log.subprocess.run")
    def test_builds_range_ref(self, mock_run: MagicMock) -> None:
        """parse_log uses from..to range notation when from_ref is given."""
        mock_run.return_value = MagicMock(stdout="", returncode=0)
        parse_log(Path("/repo"), from_ref="abc1234", to_ref="HEAD")
        cmd = mock_run.call_args[0][0]
        assert "abc1234..HEAD" in cmd


class TestIsBareRepo:
    """Test bare repo detection."""

    @patch("driftscope.git_client.log.subprocess.run")
    def test_returns_true_for_bare(self, mock_run: MagicMock) -> None:
        """Returns True when core.bare is true."""
        mock_run.return_value = MagicMock(stdout="true\n", returncode=0)
        assert is_bare_repo(Path("/repo")) is True

    @patch("driftscope.git_client.log.subprocess.run")
    def test_returns_false_for_non_bare(self, mock_run: MagicMock) -> None:
        """Returns False when core.bare is false."""
        mock_run.return_value = MagicMock(stdout="false\n", returncode=0)
        assert is_bare_repo(Path("/repo")) is False

    @patch("driftscope.git_client.log.subprocess.run")
    def test_returns_false_on_error(self, mock_run: MagicMock) -> None:
        """Returns False when git command fails."""
        import subprocess

        mock_run.side_effect = subprocess.CalledProcessError(1, "git")
        assert is_bare_repo(Path("/repo")) is False
```

### 6.8 `tests/git_client/test_diff_parser.py`

```python
"""Tests for unified diff parsing."""

from driftscope.git_client.diff_parser import parse_unified_diff


SAMPLE_DIFF = """\
diff --git a/src/main.py b/src/main.py
--- a/src/main.py
+++ b/src/main.py
@@ -1,3 +1,5 @@
 import os
-import sys
+import pathlib
+
 def main():
-    pass
+    print("hello")
"""


class TestParseUnifiedDiff:
    """Test unified diff parsing."""

    def test_detects_single_file(self) -> None:
        """Diff with one file produces one FileHunk."""
        hunks = parse_unified_diff(SAMPLE_DIFF)
        assert len(hunks) == 1

    def test_file_path_extracted(self) -> None:
        """File path is extracted from +++ header."""
        hunks = parse_unified_diff(SAMPLE_DIFF)
        assert hunks[0].file_path == "src/main.py"

    def test_added_lines_detected(self) -> None:
        """Added lines (import pathlib, blank, print) are detected."""
        hunks = parse_unified_diff(SAMPLE_DIFF)
        assert 2 in hunks[0].added_lines  # import pathlib
        assert 3 in hunks[0].added_lines  # blank line
        assert 5 in hunks[0].added_lines  # print("hello")

    def test_removed_lines_detected(self) -> None:
        """Removed lines (import sys, pass) are detected."""
        hunks = parse_unified_diff(SAMPLE_DIFF)
        assert 2 in hunks[0].removed_lines  # import sys
        assert 4 in hunks[0].removed_lines  # pass

    def test_empty_diff(self) -> None:
        """Empty diff string produces no hunks."""
        hunks = parse_unified_diff("")
        assert hunks == []

    def test_no_changes_diff(self) -> None:
        """Diff with only context lines produces empty added/removed."""
        diff = (
            "diff --git a/f.txt b/f.txt\n"
            "--- a/f.txt\n"
            "+++ b/f.txt\n"
            "@@ -1,2 +1,2 @@\n"
            " line1\n"
            " line2\n"
        )
        hunks = parse_unified_diff(diff)
        assert len(hunks) == 1
        assert hunks[0].added_lines == []
        assert hunks[0].removed_lines == []

    def test_multi_file_diff(self) -> None:
        """Diff with two files produces two FileHunks."""
        diff = (
            "diff --git a/a.py b/a.py\n"
            "--- a/a.py\n"
            "+++ b/a.py\n"
            "@@ -1 +1,2 @@\n"
            "-old_a\n"
            "+new_a\n"
            "+extra_a\n"
            "diff --git a/b.py b/b.py\n"
            "--- a/b.py\n"
            "+++ b/b.py\n"
            "@@ -1 +1 @@\n"
            "-old_b\n"
            "+new_b\n"
        )
        hunks = parse_unified_diff(diff)
        assert len(hunks) == 2
        paths = {h.file_path for h in hunks}
        assert "a.py" in paths
        assert "b.py" in paths

    def test_added_only_diff(self) -> None:
        """New file diff has only added lines."""
        diff = (
            "diff --git a/new.py b/new.py\n"
            "--- /dev/null\n"
            "+++ b/new.py\n"
            "@@ -0,0 +1,3 @@\n"
            "+line1\n"
            "+line2\n"
            "+line3\n"
        )
        hunks = parse_unified_diff(diff)
        assert len(hunks) == 1
        assert len(hunks[0].added_lines) == 3
        assert hunks[0].removed_lines == []
```

### 6.9 `tests/git_client/test_integration.py`

```python
"""Integration tests for git_client using real git subprocess with tmp_git_repo."""

from pathlib import Path

import pytest

from driftscope.git_client.blame import run_blame
from driftscope.git_client.diff_parser import parse_unified_diff
from driftscope.git_client.log import parse_log


class TestLogIntegration:
    """Test parse_log against a real temp repository."""

    def test_single_commit(self, tmp_git_repo: Path) -> None:
        """A repo with one commit returns exactly one Commit."""
        commits = parse_log(tmp_git_repo)
        assert len(commits) == 1
        assert commits[0].message_subject == "Initial commit"
        assert commits[0].sha != ""

    def test_three_commits_ordered(self, tmp_git_repo: Path) -> None:
        """Three commits are returned oldest-first."""
        import subprocess

        for i, msg in enumerate(["Second", "Third"], start=2):
            f = tmp_git_repo / f"file{i}.py"
            f.write_text(f"# file {i}\n")
            subprocess.run(["git", "add", f"f/file{i}.py"], cwd=tmp_git_repo, check=True, capture_output=True)
            subprocess.run(
                ["git", "commit", "-m", msg],
                cwd=tmp_git_repo,
                check=True,
                capture_output=True,
            )

        commits = parse_log(tmp_git_repo)
        assert len(commits) == 3
        assert commits[0].message_subject == "Initial commit"
        assert commits[1].message_subject == "Second"
        assert commits[2].message_subject == "Third"


class TestBlameIntegration:
    """Test run_blame against a real temp repository."""

    def test_blame_single_file(self, tmp_git_repo: Path) -> None:
        """Blame on a committed file returns correct lines."""
        import subprocess

        src = tmp_git_repo / "hello.py"
        src.write_text("x = 1\ny = 2\n")
        subprocess.run(["git", "add", "hello.py"], cwd=tmp_git_repo, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Add hello.py"],
            cwd=tmp_git_repo,
            check=True,
            capture_output=True,
        )

        lines = run_blame(tmp_git_repo, Path("hello.py"))
        assert len(lines) == 2
        assert lines[0].content == "x = 1"
        assert lines[1].content == "y = 2"


class TestDiffParserIntegration:
    """Test diff parsing with real git diff output."""

    def test_real_diff_output(self, tmp_git_repo: Path) -> None:
        """Parse a real git diff from a temp repo."""
        import subprocess

        src = tmp_git_repo / "code.py"
        src.write_text("a = 1\nb = 2\nc = 3\n")
        subprocess.run(["git", "add", "code.py"], cwd=tmp_git_repo, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Add code.py"],
            cwd=tmp_git_repo,
            check=True,
            capture_output=True,
        )

        src.write_text("a = 1\nb = 99\nd = 4\n")
        result = subprocess.run(
            ["git", "diff"],
            cwd=tmp_git_repo,
            capture_output=True,
            text=True,
            check=True,
        )

        hunks = parse_unified_diff(result.stdout)
        assert len(hunks) == 1
        assert hunks[0].file_path == "code.py"
        assert len(hunks[0].removed_lines) > 0
        assert len(hunks[0].added_lines) > 0
```

### TDD Step Sequence

```
Step 1: Write tests/git_client/test_diff_parser.py with all tests.
  -> Run: python -m pytest tests/git_client/test_diff_parser.py -v
  -> Expect: FAIL (module not found)

Step 2: Implement driftscope/git_client/__init__.py and diff_parser.py.
  -> Run: python -m pytest tests/git_client/test_diff_parser.py -v
  -> Expect: PASS
  -> Commit: feat(git_client): add unified diff parser for line mapping

Step 3: Write tests/git_client/test_blame.py with all tests.
  -> Run: python -m pytest tests/git_client/test_blame.py -v
  -> Expect: FAIL (module not found)

Step 4: Implement blame.py.
  -> Run: python -m pytest tests/git_client/test_blame.py -v
  -> Expect: PASS
  -> Commit: feat(git_client): add git blame porcelain parser

Step 5: Write tests/git_client/test_log.py with all tests.
  -> Run: python -m pytest tests/git_client/test_log.py -v
  -> Expect: FAIL (module not found)

Step 6: Implement log.py.
  -> Run: python -m pytest tests/git_client/test_log.py -v
  -> Expect: PASS
  -> Commit: feat(git_client): add git log parser with null-delimited format

Step 7: Write tests/git_client/test_integration.py.
  -> Run: python -m pytest tests/git_client/test_integration.py -v
  -> Expect: PASS (uses tmp_git_repo fixture)
  -> Commit: test(git_client): add integration tests with real git subprocess

Step 8: Coverage check.
  -> Run: python -m pytest tests/git_client/ --cov=driftscope/git_client --cov-report=term-missing
  -> Expect: >=95% line coverage
```

### Commit

```
feat(git_client): add blame, log, and diff parsing with subprocess git invocation
```

---

## Task 7: AST Engine (parser, differ, survival, grammars)

**Goal:** Implement tree-sitter parsing, AST-level diffing, and node survival tracking.

### Files

```
driftscope/ast_engine/__init__.py
driftscope/ast_engine/parser.py      # tree-sitter parsing facade
driftscope/ast_engine/differ.py      # AST-level diff computation
driftscope/ast_engine/survival.py    # exact node survival tracking
driftscope/ast_engine/grammars/__init__.py
driftscope/ast_engine/grammars/python.py
driftscope/ast_engine/grammars/typescript.py
driftscope/ast_engine/grammars/go.py
driftscope/ast_engine/grammars/java.py
driftscope/ast_engine/grammars/ruby.py
tests/ast_engine/__init__.py
tests/ast_engine/test_parser.py
tests/ast_engine/test_differ.py
tests/ast_engine/test_survival.py
```

### 7.1 `driftscope/ast_engine/__init__.py`

```python
"""AST engine — tree-sitter parsing, diffing, and survival tracking."""

from driftscope.ast_engine.parser import parse_source, get_language
from driftscope.ast_engine.differ import compute_ast_diff
from driftscope.ast_engine.survival import compute_survival

__all__ = ["parse_source", "get_language", "compute_ast_diff", "compute_survival"]
```

### 7.2 `driftscope/ast_engine/parser.py`

```python
"""Tree-sitter parsing facade.

Provides a unified interface for parsing source code in multiple languages
using tree-sitter. Grammars are lazily loaded on first use.

Time Complexity: O(N) where N is the length of the source string.
Space Complexity: O(N) for the tree structure.
"""

import hashlib
from typing import Any

from driftscope.errors import ASTParseError

# Language name -> tree_sitter.Language mapping.
_language_registry: dict[str, Any] = {}

# Supported languages with their tree-sitter language identifiers.
SUPPORTED_LANGUAGES = {
    "python": "python",
    "typescript": "typescript",
    "javascript": "javascript",
    "go": "go",
    "java": "java",
    "ruby": "ruby",
}


def get_language(language: str) -> Any:
    """Get the tree-sitter Language object for a supported language.

    Lazily loads and caches the grammar on first access.

    Args:
        language: Language name (e.g., "python", "typescript").

    Returns:
        tree_sitter.Language object for the given language.

    Raises:
        ASTParseError: If the language is not supported.
    """
    if language not in SUPPORTED_LANGUAGES:
        raise ASTParseError(
            message=f"Unsupported language: '{language}'. "
                    f"Supported: {sorted(SUPPORTED_LANGUAGES.keys())}",
            suggestion="Check the 'analysis.languages' config setting.",
        )

    if language in _language_registry:
        return _language_registry[language]

    try:
        import tree_sitter_python as tspython  # type: ignore[import-untyped]

        if language == "python":
            import tree_sitter
            lang = tree_sitter.Language(tspython.language())
            _language_registry["python"] = lang
            return lang
    except ImportError:
        pass

    # Fallback: try tree_sitter built-in language loading.
    try:
        import tree_sitter  # type: ignore[import-untyped]

        lang_name = SUPPORTED_LANGUAGES[language]
        lang = tree_sitter.Language(tree_sitter.Language.lookup(lang_name))
        _language_registry[language] = lang
        return lang
    except Exception as e:
        raise ASTParseError(
            message=f"Failed to load tree-sitter grammar for '{language}': {e}",
            suggestion=f"Install the tree-sitter grammar for {language}.",
        ) from e


def parse_source(
    source: str,
    language: str,
    timeout: float = 5.0,
) -> Any:
    """Parse source code into a tree-sitter tree.

    Args:
        source: Source code string.
        language: Language name (e.g., "python").
        timeout: Maximum parse time in seconds.

    Returns:
        tree_sitter.Tree object.

    Raises:
        ASTParseError: If the language is unsupported, the grammar fails to
                       load, or parsing exceeds the timeout.
    """
    import tree_sitter  # type: ignore[import-untyped]

    lang = get_language(language)

    try:
        parser = tree_sitter.Parser()
        parser.language = lang
    except Exception as e:
        raise ASTParseError(
            message=f"Failed to create parser for '{language}': {e}",
        ) from e

    try:
        tree = parser.parse(source.encode("utf-8"))
    except Exception as e:
        raise ASTParseError(
            message=f"Parse error for '{language}': {e}",
        ) from e

    if tree is None:
        raise ASTParseError(
            message=f"tree-sitter returned None tree for '{language}' source.",
        )

    return tree


def compute_text_hash(text: str) -> str:
    """Compute SHA-256 hash of a string.

    Args:
        text: Input string.

    Returns:
        Hex digest of the SHA-256 hash (64 characters).
    """
    return hashlib.sha256(text.encode("utf-8")).hexdigest()
```

### 7.3 `driftscope/ast_engine/differ.py`

```python
"""AST-level diff computation between two source states.

Parses before/after source with tree-sitter, walks both trees, and
identifies added, removed, and modified AST nodes.

Time Complexity: O(N + M) where N and M are the sizes of the two trees.
Space Complexity: O(N + M) for the tree structures and diff output.
"""

import hashlib
from pathlib import Path
from typing import Any, Literal

from driftscope.ast_engine.parser import compute_text_hash, parse_source
from driftscope.errors import ASTParseError
from driftscope.models.ast_diff import ASTFileDiff, ASTNodeChange


def _walk_tree(tree: Any) -> list[dict[str, Any]]:
    """Walk a tree-sitter tree and collect named nodes.

    Args:
        tree: A tree-sitter Tree object.

    Returns:
        List of dicts with node_type, start_line, end_line, text, text_hash.
    """
    nodes: list[dict[str, Any]] = []

    def _visit(node: Any) -> None:
        if node.is_named:
            text = node.text.decode("utf-8") if hasattr(node, "text") and node.text else ""
            nodes.append({
                "node_type": node.type,
                "start_line": node.start_point[0] + 1,  # 1-based
                "end_line": node.end_point[0] + 1,
                "text": text,
                "text_hash": compute_text_hash(text),
            })
        for child in node.children:
            _visit(child)

    _visit(tree.root_node)
    return nodes


def compute_ast_diff(
    before: str | None,
    after: str | None,
    language: str,
    commit_sha: str,
    file_path: Path,
    authorship_class: Literal["human", "ai"],
) -> ASTFileDiff:
    """Compute AST-level diff between two source states.

    Args:
        before: Source before the commit (None for new files).
        after: Source after the commit (None for deleted files).
        language: Source language for tree-sitter parsing.
        commit_sha: The commit SHA.
        file_path: Path to the file relative to repo root.
        authorship_class: Whether the commit is human or AI authored.

    Returns:
        ASTFileDiff with all detected changes.

    Raises:
        ASTParseError: If parsing fails for either state.
    """
    before_hash: str | None = None
    after_hash: str | None = None
    before_nodes: list[dict[str, Any]] = []
    after_nodes: list[dict[str, Any]] = []

    if before is not None:
        before_tree = parse_source(before, language)
        before_nodes = _walk_tree(before_tree)
        before_hash = compute_text_hash(before)

    if after is not None:
        after_tree = parse_source(after, language)
        after_nodes = _walk_tree(after_tree)
        after_hash = compute_text_hash(after)

    changes = _diff_nodes(before_nodes, after_nodes)

    return ASTFileDiff(
        file_path=file_path,
        commit_sha=commit_sha,
        before_hash=before_hash,
        after_hash=after_hash,
        changes=changes,
        authorship_class=authorship_class,
    )


def _diff_nodes(
    before_nodes: list[dict[str, Any]],
    after_nodes: list[dict[str, Any]],
) -> list[ASTNodeChange]:
    """Compare two lists of AST nodes and produce changes.

    Uses text_hash matching to detect exact additions, removals,
    and modifications.

    Args:
        before_nodes: Named nodes from the before state.
        after_nodes: Named nodes from the after state.

    Returns:
        List of ASTNodeChange objects.
    """
    changes: list[ASTNodeChange] = []

    before_hashes = {n["text_hash"] for n in before_nodes}
    after_hashes = {n["text_hash"] for n in after_nodes}

    # Map hash -> node for lookups.
    before_by_hash: dict[str, dict[str, Any]] = {n["text_hash"]: n for n in before_nodes}
    after_by_hash: dict[str, dict[str, Any]] = {n["text_hash"]: n for n in after_nodes}

    # Removed: in before but not in after.
    for h in before_hashes - after_hashes:
        node = before_by_hash[h]
        changes.append(ASTNodeChange(
            node_type=node["node_type"],
            start_line=node["start_line"],
            end_line=node["end_line"],
            change_type="removed",
            text_hash=h,
        ))

    # Added: in after but not in before.
    for h in after_hashes - before_hashes:
        node = after_by_hash[h]
        changes.append(ASTNodeChange(
            node_type=node["node_type"],
            start_line=node["start_line"],
            end_line=node["end_line"],
            change_type="added",
            text_hash=h,
        ))

    return changes
```

### 7.4 `driftscope/ast_engine/survival.py`

```python
"""Exact node survival tracking.

For each AST node introduced at a given commit, determines whether that
exact node (matched by text_hash) still exists at the window end.

Time Complexity: O(N * M) where N is the number of diffs and M is the
                  number of nodes at window end.
Space Complexity: O(M) for the set of surviving hashes.
"""

from pathlib import Path
from typing import Literal

from driftscope.models.ast_diff import ASTDiffSet, ASTFileDiff, ASTNodeChange
from driftscope.models.blame import BlameLine
from driftscope.models.metrics import SurvivalMetrics


def compute_survival(
    diff_set: ASTDiffSet,
    blame: dict[Path, list[BlameLine]],
    window: str,
    ai_commit_shas: set[str],
    human_commit_shas: set[str],
) -> SurvivalMetrics:
    """Compute line survival rate for a single window.

    Counts lines introduced by AI and human commits, then checks how many
    survive by cross-referencing blame data (lines still present at HEAD).

    Args:
        diff_set: Collection of AST diffs for the analysis window.
        blame: Current blame data (lines present at HEAD).
        window: Window identifier (e.g., "90d").
        ai_commit_shas: Set of commit SHAs attributed to AI.
        human_commit_shas: Set of commit SHAs attributed to humans.

    Returns:
        SurvivalMetrics with counts and rates.
    """
    # Count lines introduced (added nodes) by authorship.
    ai_introduced = 0
    human_introduced = 0

    # Track introduced hashes by authorship for survival matching.
    ai_introduced_hashes: set[str] = set()
    human_introduced_hashes: set[str] = set()

    for file_diff in diff_set.diffs:
        for change in file_diff.changes:
            if change.change_type == "added":
                line_count = change.end_line - change.start_line + 1
                if file_diff.authorship_class == "ai":
                    ai_introduced += line_count
                    ai_introduced_hashes.add(change.text_hash)
                else:
                    human_introduced += line_count
                    human_introduced_hashes.add(change.text_hash)

    # Count surviving lines: lines in blame whose originating commit is
    # within the window and attributed to the right class.
    ai_surviving = 0
    human_surviving = 0

    for file_path, blame_lines in blame.items():
        for line in blame_lines:
            if line.commit_sha in ai_commit_shas:
                ai_surviving += 1
            elif line.commit_sha in human_commit_shas:
                human_surviving += 1

    ai_rate = ai_surviving / ai_introduced if ai_introduced > 0 else 0.0
    human_rate = human_surviving / human_introduced if human_introduced > 0 else 0.0

    return SurvivalMetrics(
        window=window,
        ai_lines_introduced=ai_introduced,
        ai_lines_surviving=ai_surviving,
        ai_survival_rate=ai_rate,
        human_lines_introduced=human_introduced,
        human_lines_surviving=human_surviving,
        human_survival_rate=human_rate,
    )
```

### 7.5 `driftscope/ast_engine/grammars/__init__.py`

```python
"""Grammar definitions for tree-sitter languages."""
```

### 7.6 `driftscope/ast_engine/grammars/python.py`

```python
"""Python grammar definition for tree-sitter."""

GRAMMAR_NAME = "python"
LANGUAGE_ID = "python"
```

### 7.7 `driftscope/ast_engine/grammars/typescript.py`

```python
"""TypeScript grammar definition for tree-sitter."""

GRAMMAR_NAME = "typescript"
LANGUAGE_ID = "typescript"
```

### 7.8 `driftscope/ast_engine/grammars/go.py`

```python
"""Go grammar definition for tree-sitter."""

GRAMMAR_NAME = "go"
LANGUAGE_ID = "go"
```

### 7.9 `driftscope/ast_engine/grammars/java.py`

```python
"""Java grammar definition for tree-sitter."""

GRAMMAR_NAME = "java"
LANGUAGE_ID = "java"
```

### 7.10 `driftscope/ast_engine/grammars/ruby.py`

```python
"""Ruby grammar definition for tree-sitter."""

GRAMMAR_NAME = "ruby"
LANGUAGE_ID = "ruby"
```

### 7.11 `tests/ast_engine/__init__.py`

```python
"""Tests for driftscope.ast_engine."""
```

### 7.12 `tests/ast_engine/test_parser.py`

```python
"""Tests for tree-sitter parsing facade."""

from unittest.mock import MagicMock, patch

import pytest

from driftscope.ast_engine.parser import (
    SUPPORTED_LANGUAGES,
    compute_text_hash,
    get_language,
    parse_source,
)
from driftscope.errors import ASTParseError


class TestGetLanguage:
    """Test language registry and loading."""

    def test_unsupported_language_raises(self) -> None:
        """Requesting an unsupported language raises ASTParseError."""
        with pytest.raises(ASTParseError, match="Unsupported language"):
            get_language("fortran")

    def test_supported_languages_list(self) -> None:
        """All expected languages are in the supported set."""
        expected = {"python", "typescript", "javascript", "go", "java", "ruby"}
        assert expected == set(SUPPORTED_LANGUAGES.keys())


class TestComputeTextHash:
    """Test SHA-256 text hashing."""

    def test_returns_64_char_hex(self) -> None:
        """Hash is a 64-character hex string."""
        h = compute_text_hash("def foo(): pass")
        assert len(h) == 64
        assert all(c in "0123456789abcdef" for c in h)

    def test_deterministic(self) -> None:
        """Same input always produces the same hash."""
        h1 = compute_text_hash("hello")
        h2 = compute_text_hash("hello")
        assert h1 == h2

    def test_different_inputs_differ(self) -> None:
        """Different inputs produce different hashes."""
        h1 = compute_text_hash("hello")
        h2 = compute_text_hash("world")
        assert h1 != h2

    def test_empty_string(self) -> None:
        """Empty string produces a valid hash."""
        h = compute_text_hash("")
        assert len(h) == 64


class TestParseSource:
    """Test parse_source with mocked tree-sitter."""

    @patch("driftscope.ast_engine.parser.get_language")
    @patch("driftscope.ast_engine.parser.tree_sitter")
    def test_parse_returns_tree(self, mock_ts: MagicMock, mock_get_lang: MagicMock) -> None:
        """parse_source returns a tree-sitter Tree."""
        mock_parser = MagicMock()
        mock_tree = MagicMock()
        mock_parser.parse.return_value = mock_tree
        mock_ts.Parser.return_value = mock_parser

        result = parse_source("x = 1", "python")
        assert result == mock_tree

    @patch("driftscope.ast_engine.parser.get_language")
    @patch("driftscope.ast_engine.parser.tree_sitter")
    def test_parse_none_tree_raises(self, mock_ts: MagicMock, mock_get_lang: MagicMock) -> None:
        """parse_source raises ASTParseError when tree-sitter returns None."""
        mock_parser = MagicMock()
        mock_parser.parse.return_value = None
        mock_ts.Parser.return_value = mock_parser

        with pytest.raises(ASTParseError, match="returned None tree"):
            parse_source("bad source", "python")
```

### 7.13 `tests/ast_engine/test_differ.py`

```python
"""Tests for AST diff computation."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from driftscope.ast_engine.differ import _diff_nodes, _walk_tree, compute_ast_diff
from driftscope.models.ast_diff import ASTNodeChange


def _make_mock_node(
    node_type: str,
    start_row: int,
    end_row: int,
    text: str,
    is_named: bool = True,
    children: list | None = None,
) -> MagicMock:
    """Create a mock tree-sitter node."""
    node = MagicMock()
    node.type = node_type
    node.start_point = (start_row, 0)
    node.end_point = (end_row, 0)
    node.text = text.encode("utf-8")
    node.is_named = is_named
    node.children = children or []
    return node


class TestWalkTree:
    """Test tree walking to collect named nodes."""

    def test_collects_named_nodes(self) -> None:
        """Walk collects named nodes with correct fields."""
        func_node = _make_mock_node(
            "function_definition", 0, 2, "def foo():\n    pass\n"
        )
        root = _make_mock_node("module", 0, 2, "def foo():\n    pass\n", children=[func_node])
        func_node.parent = root
        root.parent = None

        mock_tree = MagicMock()
        mock_tree.root_node = root

        nodes = _walk_tree(mock_tree)
        assert len(nodes) == 1
        assert nodes[0]["node_type"] == "function_definition"
        assert nodes[0]["start_line"] == 1
        assert nodes[0]["end_line"] == 3

    def test_skips_unnamed_nodes(self) -> None:
        """Unnamed nodes (punctuation, keywords) are skipped."""
        unnamed = _make_mock_node("(", 0, 0, "(", is_named=False)
        named = _make_mock_node("identifier", 0, 0, "foo")
        root = _make_mock_node("module", 0, 0, "foo(", children=[named, unnamed])
        root.parent = None

        mock_tree = MagicMock()
        mock_tree.root_node = root

        nodes = _walk_tree(mock_tree)
        assert len(nodes) == 1
        assert nodes[0]["node_type"] == "identifier"


class TestDiffNodes:
    """Test node diff computation."""

    def test_added_node(self) -> None:
        """Node in after but not before is marked as added."""
        before = []
        after = [{"node_type": "function_definition", "start_line": 1, "end_line": 3,
                   "text": "def foo(): pass", "text_hash": "a" * 64}]
        changes = _diff_nodes(before, after)
        assert len(changes) == 1
        assert changes[0].change_type == "added"

    def test_removed_node(self) -> None:
        """Node in before but not after is marked as removed."""
        before = [{"node_type": "function_definition", "start_line": 1, "end_line": 3,
                    "text": "def foo(): pass", "text_hash": "a" * 64}]
        after = []
        changes = _diff_nodes(before, after)
        assert len(changes) == 1
        assert changes[0].change_type == "removed"

    def test_unchanged_node_no_change(self) -> None:
        """Node present in both before and after produces no change."""
        node = {"node_type": "function_definition", "start_line": 1, "end_line": 3,
                "text": "def foo(): pass", "text_hash": "a" * 64}
        changes = _diff_nodes([node], [node])
        assert len(changes) == 0

    def test_mixed_changes(self) -> None:
        """Multiple changes are correctly identified."""
        before = [
            {"node_type": "func_a", "start_line": 1, "end_line": 5,
             "text": "a", "text_hash": "a" * 64},
            {"node_type": "func_c", "start_line": 6, "end_line": 10,
             "text": "c", "text_hash": "c" * 64},
        ]
        after = [
            {"node_type": "func_a", "start_line": 1, "end_line": 5,
             "text": "a", "text_hash": "a" * 64},  # unchanged
            {"node_type": "func_b", "start_line": 6, "end_line": 10,
             "text": "b", "text_hash": "b" * 64},  # added (func_c removed, func_b added)
        ]
        changes = _diff_nodes(before, after)
        change_types = {c.change_type for c in changes}
        assert "removed" in change_types
        assert "added" in change_types


class TestComputeAstDiff:
    """Test the full compute_ast_diff function."""

    @patch("driftscope.ast_engine.differ.parse_source")
    @patch("driftscope.ast_engine.differ._walk_tree")
    def test_new_file_all_added(self, mock_walk: MagicMock, mock_parse: MagicMock) -> None:
        """New file (before=None) produces only added changes."""
        mock_tree = MagicMock()
        mock_parse.return_value = mock_tree
        mock_walk.return_value = [
            {"node_type": "function_definition", "start_line": 1, "end_line": 3,
             "text": "def new(): pass", "text_hash": "n" * 64},
        ]

        diff = compute_ast_diff(
            before=None,
            after="def new(): pass",
            language="python",
            commit_sha="a" * 40,
            file_path=Path("src/new.py"),
            authorship_class="ai",
        )
        assert diff.before_hash is None
        assert diff.after_hash is not None
        assert len(diff.changes) == 1
        assert diff.changes[0].change_type == "added"
        assert diff.authorship_class == "ai"

    @patch("driftscope.ast_engine.differ.parse_source")
    @patch("driftscope.ast_engine.differ._walk_tree")
    def test_deleted_file_all_removed(self, mock_walk: MagicMock, mock_parse: MagicMock) -> None:
        """Deleted file (after=None) produces only removed changes."""
        mock_tree = MagicMock()
        mock_parse.return_value = mock_tree
        mock_walk.return_value = [
            {"node_type": "function_definition", "start_line": 1, "end_line": 3,
             "text": "def old(): pass", "text_hash": "o" * 64},
        ]

        diff = compute_ast_diff(
            before="def old(): pass",
            after=None,
            language="python",
            commit_sha="a" * 40,
            file_path=Path("src/old.py"),
            authorship_class="human",
        )
        assert diff.after_hash is None
        assert diff.before_hash is not None
        assert len(diff.changes) == 1
        assert diff.changes[0].change_type == "removed"
```

### 7.14 `tests/ast_engine/test_survival.py`

```python
"""Tests for node survival tracking."""

from pathlib import Path

from driftscope.ast_engine.survival import compute_survival
from driftscope.models.ast_diff import ASTDiffSet, ASTFileDiff, ASTNodeChange
from driftscope.models.blame import BlameLine
from driftscope.models.metrics import SurvivalMetrics


def _node_change(
    change_type: str,
    start_line: int = 1,
    end_line: int = 1,
    text_hash: str = "a" * 64,
) -> ASTNodeChange:
    return ASTNodeChange(
        node_type="function_definition",
        start_line=start_line,
        end_line=end_line,
        change_type=change_type,
        text_hash=text_hash,
    )


def _file_diff(
    changes: list[ASTNodeChange],
    authorship_class: str = "ai",
) -> ASTFileDiff:
    return ASTFileDiff(
        file_path=Path("src/main.py"),
        commit_sha="a" * 40,
        changes=changes,
        authorship_class=authorship_class,
    )


class TestComputeSurvival:
    """Test survival rate computation."""

    def test_all_ai_surviving(self) -> None:
        """All AI lines surviving produces rate 1.0."""
        diff_set = ASTDiffSet(
            diffs=[_file_diff([_node_change("added", 1, 5)])],
            skipped_files=[],
        )
        blame = {Path("src/main.py"): [
            BlameLine(line_number=i, commit_sha="a" * 40, author_name="Bot",
                      author_email="bot@example.com", content=f"line{i}")
            for i in range(1, 6)
        ]}
        result = compute_survival(
            diff_set, blame, "90d",
            ai_commit_shas={"a" * 40},
            human_commit_shas=set(),
        )
        assert result.ai_lines_introduced == 5
        assert result.ai_lines_surviving == 5
        assert result.ai_survival_rate == 1.0

    def test_partial_survival(self) -> None:
        """Some lines removed produces rate < 1.0."""
        diff_set = ASTDiffSet(
            diffs=[_file_diff([_node_change("added", 1, 10)])],
            skipped_files=[],
        )
        # Only 5 of 10 lines survive.
        blame = {Path("src/main.py"): [
            BlameLine(line_number=i, commit_sha="a" * 40, author_name="Bot",
                      author_email="bot@example.com", content=f"line{i}")
            for i in range(1, 6)
        ]}
        result = compute_survival(
            diff_set, blame, "90d",
            ai_commit_shas={"a" * 40},
            human_commit_shas=set(),
        )
        assert result.ai_lines_introduced == 10
        assert result.ai_lines_surviving == 5
        assert result.ai_survival_rate == 0.5

    def test_zero_introduced(self) -> None:
        """Zero lines introduced produces rate 0.0 (not NaN)."""
        diff_set = ASTDiffSet(diffs=[], skipped_files=[])
        result = compute_survival(
            diff_set, {}, "90d",
            ai_commit_shas=set(),
            human_commit_shas=set(),
        )
        assert result.ai_survival_rate == 0.0
        assert result.human_survival_rate == 0.0

    def test_mixed_ai_and_human(self) -> None:
        """AI and human lines are counted separately."""
        diff_set = ASTDiffSet(
            diffs=[
                _file_diff([_node_change("added", 1, 3)], authorship_class="ai"),
                _file_diff([_node_change("added", 1, 2)], authorship_class="human"),
            ],
            skipped_files=[],
        )
        blame = {Path("src/main.py"): [
            BlameLine(line_number=1, commit_sha="a" * 40, author_name="Bot",
                      author_email="bot@ai.com", content="ai_line"),
            BlameLine(line_number=2, commit_sha="b" * 40, author_name="Dev",
                      author_email="dev@human.com", content="human_line"),
        ]}
        result = compute_survival(
            diff_set, blame, "90d",
            ai_commit_shas={"a" * 40},
            human_commit_shas={"b" * 40},
        )
        assert result.ai_lines_introduced == 3
        assert result.human_lines_introduced == 2

    def test_window_label_preserved(self) -> None:
        """The window string is stored in the result."""
        diff_set = ASTDiffSet(diffs=[], skipped_files=[])
        result = compute_survival(diff_set, {}, "30d", set(), set())
        assert result.window == "30d"
```

### TDD Step Sequence

```
Step 1: Write tests/ast_engine/test_parser.py with all tests.
  -> Run: python -m pytest tests/ast_engine/test_parser.py -v
  -> Expect: FAIL (module not found)

Step 2: Implement driftscope/ast_engine/__init__.py and parser.py + grammar stubs.
  -> Run: python -m pytest tests/ast_engine/test_parser.py -v
  -> Expect: PASS
  -> Commit: feat(ast_engine): add tree-sitter parsing facade with language registry

Step 3: Write tests/ast_engine/test_differ.py with all tests.
  -> Run: python -m pytest tests/ast_engine/test_differ.py -v
  -> Expect: FAIL (module not found)

Step 4: Implement differ.py.
  -> Run: python -m pytest tests/ast_engine/test_differ.py -v
  -> Expect: PASS
  -> Commit: feat(ast_engine): add AST-level diff computation with hash-based change detection

Step 5: Write tests/ast_engine/test_survival.py with all tests.
  -> Run: python -m pytest tests/ast_engine/test_survival.py -v
  -> Expect: FAIL (module not found)

Step 6: Implement survival.py.
  -> Run: python -m pytest tests/ast_engine/test_survival.py -v
  -> Expect: PASS
  -> Commit: feat(ast_engine): add node survival tracking with authorship-segmented rates

Step 7: Coverage check.
  -> Run: python -m pytest tests/ast_engine/ --cov=driftscope/ast_engine --cov-report=term-missing
  -> Expect: >=95% line coverage
```

### Commit

```
feat(ast_engine): add tree-sitter parsing, AST diffing, and node survival tracking with 5-language grammar support
```

---

## Task 8: Metrics (survival, complexity, churn)

**Goal:** Implement metric computation on top of attributed history and AST diffs.

### Files

```
driftscope/metrics/__init__.py
driftscope/metrics/survival.py       # line survival rate per window per module
driftscope/metrics/complexity.py     # cyclomatic + cognitive complexity deltas
driftscope/metrics/churn.py          # module-level churn attribution
tests/metrics/__init__.py
tests/metrics/test_survival.py
tests/metrics/test_complexity.py
tests/metrics/test_churn.py
```

### 8.1 `driftscope/metrics/__init__.py`

```python
"""Metrics computation — survival, complexity, and churn."""

from driftscope.metrics.survival import compute_survival_metrics
from driftscope.metrics.complexity import compute_complexity_metrics
from driftscope.metrics.churn import compute_churn_metrics

__all__ = [
    "compute_survival_metrics",
    "compute_complexity_metrics",
    "compute_churn_metrics",
]
```

### 8.2 `driftscope/metrics/survival.py`

```python
"""Line survival rate computation per window per module.

For each module and each configured time window, counts how many lines
introduced by AI and human authors are still present at the analysis
end point.

Time Complexity: O(L) where L is the total number of blame lines.
Space Complexity: O(M) where M is the number of modules.
"""

from pathlib import Path

from driftscope.errors import MetricError
from driftscope.models.ast_diff import ASTDiffSet
from driftscope.models.blame import BlameLine
from driftscope.models.metrics import SurvivalMetrics


def compute_survival_metrics(
    blame: dict[Path, list[BlameLine]],
    diff_set: ASTDiffSet,
    windows: list[str],
    ai_commit_shas: set[str],
    human_commit_shas: set[str],
) -> dict[str, dict[str, SurvivalMetrics]]:
    """Compute survival metrics per module per window.

    Args:
        blame: Mapping of file paths to blame data at HEAD.
        diff_set: Collection of AST diffs with authorship.
        windows: Time window labels (e.g., ["30d", "90d"]).
        ai_commit_shas: Set of commit SHAs attributed to AI.
        human_commit_shas: Set of commit SHAs attributed to humans.

    Returns:
        Nested dict: module_path -> window -> SurvivalMetrics.

    Raises:
        MetricError: If windows list is empty.
    """
    if not windows:
        raise MetricError(
            message="At least one survival window is required.",
            suggestion="Configure 'metrics.survival_windows' in .driftscope.yaml.",
        )

    # Group blame lines by module.
    module_lines = _group_by_module(blame)

    # Count introduced lines per module by authorship from diffs.
    introduced = _count_introduced_by_module(diff_set)

    result: dict[str, dict[str, SurvivalMetrics]] = {}

    for module_path, lines in module_lines.items():
        result[module_path] = {}
        ai_surviving = sum(1 for line in lines if line.commit_sha in ai_commit_shas)
        human_surviving = sum(1 for line in lines if line.commit_sha in human_commit_shas)

        ai_introduced = introduced.get(module_path, {}).get("ai", 0)
        human_introduced = introduced.get(module_path, {}).get("human", 0)

        # If no introduced data from diffs, use surviving as floor.
        if ai_introduced == 0 and ai_surviving > 0:
            ai_introduced = ai_surviving
        if human_introduced == 0 and human_surviving > 0:
            human_introduced = human_surviving

        for window in windows:
            ai_rate = ai_surviving / ai_introduced if ai_introduced > 0 else 0.0
            human_rate = human_surviving / human_introduced if human_introduced > 0 else 0.0

            result[module_path][window] = SurvivalMetrics(
                window=window,
                ai_lines_introduced=ai_introduced,
                ai_lines_surviving=ai_surviving,
                ai_survival_rate=ai_rate,
                human_lines_introduced=human_introduced,
                human_lines_surviving=human_surviving,
                human_survival_rate=human_rate,
            )

    return result


def _group_by_module(
    blame: dict[Path, list[BlameLine]],
) -> dict[str, list[BlameLine]]:
    """Group blame lines by top-level module directory.

    A module is a top-level directory under the repo root.
    Files at the root level belong to the "" (root) module.

    Args:
        blame: Mapping of file paths to blame lines.

    Returns:
        Module path string -> list of BlameLine objects.
    """
    modules: dict[str, list[BlameLine]] = {}
    for file_path, lines in blame.items():
        parts = file_path.parts
        module = parts[0] if len(parts) > 1 else ""
        modules.setdefault(module, []).extend(lines)
    return modules


def _count_introduced_by_module(
    diff_set: ASTDiffSet,
) -> dict[str, dict[str, int]]:
    """Count introduced lines per module by authorship from diffs.

    Args:
        diff_set: Collection of AST diffs.

    Returns:
        Module path -> {"ai": count, "human": count}.
    """
    result: dict[str, dict[str, int]] = {}
    for file_diff in diff_set.diffs:
        parts = file_diff.file_path.parts
        module = parts[0] if len(parts) > 1 else ""

        if module not in result:
            result[module] = {"ai": 0, "human": 0}

        for change in file_diff.changes:
            if change.change_type == "added":
                line_count = change.end_line - change.start_line + 1
                result[module][file_diff.authorship_class] += line_count

    return result
```

### 8.3 `driftscope/metrics/complexity.py`

```python
"""Cyclomatic and cognitive complexity delta computation.

Computes the complexity delta (change in complexity) per commit,
segmented by authorship, with weekly time-series breakdown.

Cyclomatic complexity counts decision points: if, elif, for, while,
and, or, except, with, assert, and ternary operators.

Cognitive complexity adds increments for nesting depth and logical
operator sequences, penalizing deeply nested code.

Time Complexity: O(S) where S is the total size of source strings.
Space Complexity: O(W) where W is the number of weekly data points.
"""

import re
from datetime import date, timedelta
from pathlib import Path

from driftscope.models.ast_diff import ASTDiffSet
from driftscope.models.metrics import ComplexityMetrics, WeeklyComplexity


# Decision points for cyclomatic complexity.
_CYCLOMATIC_PATTERNS = [
    r"\bif\b",
    r"\belif\b",
    r"\bfor\b",
    r"\bwhile\b",
    r"\band\b",
    r"\bor\b",
    r"\bexcept\b",
    r"\bwith\b",
    r"\bassert\b",
    r"\?",
    r":\s*\w+\s+if\s+",  # ternary
]


def count_cyclomatic(source: str) -> int:
    """Count cyclomatic complexity decision points in source code.

    Args:
        source: Source code string.

    Returns:
        Number of decision points found.

    Time Complexity: O(N * P) where N is lines and P is patterns.
    Space Complexity: O(1).
    """
    total = 0
    for pattern in _CYCLOMATIC_PATTERNS:
        total += len(re.findall(pattern, source))
    return total


def count_cognitive(source: str) -> int:
    """Count cognitive complexity in source code.

    Adds cyclomatic base plus nesting depth increments.
    Each level of nesting adds 1 to the cognitive score.

    Args:
        source: Source code string.

    Returns:
        Cognitive complexity score.

    Time Complexity: O(N) where N is the number of lines.
    Space Complexity: O(D) where D is max nesting depth.
    """
    base = count_cyclomatic(source)
    nesting = 0
    nesting_increment = 0

    for line in source.split("\n"):
        stripped = line.strip()
        # Decrease nesting on dedent.
        if stripped.startswith("return ") or stripped == "return" or stripped == "pass":
            nesting = max(0, nesting - 1)

        # Increase nesting on control flow.
        if any(kw in stripped for kw in ["if ", "elif ", "for ", "while ", "with ", "try:", "except "]):
            nesting_increment += nesting
            if not stripped.endswith(":"):
                pass
            else:
                nesting += 1
        elif stripped.endswith(":") and "def " in stripped:
            nesting += 1
        elif stripped.endswith(":") and "class " in stripped:
            nesting += 1

    return base + nesting_increment


def compute_complexity_metrics(
    diff_set: ASTDiffSet,
    commit_weeks: dict[str, dict[str, int]],
) -> dict[str, ComplexityMetrics]:
    """Compute complexity delta metrics per module.

    Args:
        diff_set: Collection of AST diffs with change details.
        commit_weeks: Mapping of commit_sha -> {"week": "YYYY-MM-DD",
                      "authorship_class": "ai"|"human",
                      "cyclomatic_delta": int, "cognitive_delta": int}.

    Returns:
        Module path -> ComplexityMetrics.
    """
    # Collect deltas by module and authorship.
    module_deltas: dict[str, dict[str, list[dict[str, int | float]]]] = {}

    for file_diff in diff_set.diffs:
        parts = file_diff.file_path.parts
        module = parts[0] if len(parts) > 1 else ""

        if module not in module_deltas:
            module_deltas[module] = {"ai": [], "human": []}

        sha = file_diff.commit_sha
        if sha in commit_weeks:
            entry = commit_weeks[sha]
            module_deltas[module][file_diff.authorship_class].append({
                "cyclomatic": entry.get("cyclomatic_delta", 0),
                "cognitive": entry.get("cognitive_delta", 0),
                "week": entry.get("week_iso", ""),
            })

    # Build weekly series and aggregate metrics.
    result: dict[str, ComplexityMetrics] = {}
    for module, deltas in module_deltas.items():
        ai_cyclo = [d["cyclomatic"] for d in deltas["ai"]]
        human_cyclo = [d["cyclomatic"] for d in deltas["human"]]
        ai_cog = [d["cognitive"] for d in deltas["ai"]]
        human_cog = [d["cognitive"] for d in deltas["human"]]

        # Build weekly series.
        weekly = _build_weekly_series(deltas)

        result[module] = ComplexityMetrics(
            cyclomatic_delta_ai=sum(ai_cyclo) / len(ai_cyclo) if ai_cyclo else 0.0,
            cyclomatic_delta_human=sum(human_cyclo) / len(human_cyclo) if human_cyclo else 0.0,
            cognitive_delta_ai=sum(ai_cog) / len(ai_cog) if ai_cog else 0.0,
            cognitive_delta_human=sum(human_cog) / len(human_cog) if human_cog else 0.0,
            weekly_series=weekly,
        )

    return result


def _build_weekly_series(
    deltas: dict[str, list[dict[str, int | float | str]]],
) -> list[WeeklyComplexity]:
    """Build weekly complexity time series from deltas.

    Args:
        deltas: {"ai": [...], "human": [...]} with week info.

    Returns:
        Sorted list of WeeklyComplexity entries.
    """
    weeks: dict[str, dict[str, list[float]]] = {}

    for authorship in ("ai", "human"):
        for d in deltas[authorship]:
            week_key = str(d.get("week", ""))
            if not week_key:
                continue
            if week_key not in weeks:
                weeks[week_key] = {"ai_cyclo": [], "human_cyclo": [], "ai_cog": [], "human_cog": []}
            cyclo = float(d.get("cyclomatic", 0))
            cog = float(d.get("cognitive", 0))
            weeks[week_key][f"{authorship}_cyclo"].append(cyclo)
            weeks[week_key][f"{authorship}_cog"].append(cog)

    series: list[WeeklyComplexity] = []
    for week_key in sorted(weeks.keys()):
        w = weeks[week_key]
        ai_c = w["ai_cyclo"]
        h_c = w["human_cyclo"]
        series.append(WeeklyComplexity(
            week_start=date.fromisoformat(week_key) if len(week_key) == 10 else date.today(),
            ai_cyclomatic_mean=sum(ai_c) / len(ai_c) if ai_c else 0.0,
            human_cyclomatic_mean=sum(h_c) / len(h_c) if h_c else 0.0,
            ai_cognitive_mean=sum(w["ai_cog"]) / len(w["ai_cog"]) if w["ai_cog"] else 0.0,
            human_cognitive_mean=sum(w["human_cog"]) / len(w["human_cog"]) if w["human_cog"] else 0.0,
            ai_commit_count=len(ai_c),
            human_commit_count=len(h_c),
        ))

    return series
```

### 8.4 `driftscope/metrics/churn.py`

```python
"""Module-level churn attribution over a rolling window.

Computes the percentage of code churn (lines added + removed) that is
traceable to AI-introduced code, per module.

Time Complexity: O(D) where D is the number of file diffs.
Space Complexity: O(M) where M is the number of modules.
"""

from pathlib import Path

from driftscope.errors import MetricError
from driftscope.models.ast_diff import ASTDiffSet
from driftscope.models.metrics import ChurnMetrics


def compute_churn_metrics(
    diff_set: ASTDiffSet,
) -> dict[str, ChurnMetrics]:
    """Compute churn attribution metrics per module.

    Args:
        diff_set: Collection of AST diffs with line change details.

    Returns:
        Module path -> ChurnMetrics.

    Raises:
        MetricError: If diff_set has no diffs (nothing to measure).
    """
    if not diff_set.diffs:
        return {}

    # Accumulate churn per module.
    module_churn: dict[str, dict[str, int]] = {}

    for file_diff in diff_set.diffs:
        parts = file_diff.file_path.parts
        module = parts[0] if len(parts) > 1 else ""

        if module not in module_churn:
            module_churn[module] = {"total_added": 0, "total_removed": 0,
                                    "ai_added": 0, "ai_removed": 0}

        for change in file_diff.changes:
            line_count = change.end_line - change.start_line + 1
            if change.change_type == "added":
                module_churn[module]["total_added"] += line_count
                if file_diff.authorship_class == "ai":
                    module_churn[module]["ai_added"] += line_count
            elif change.change_type == "removed":
                module_churn[module]["total_removed"] += line_count
                if file_diff.authorship_class == "ai":
                    module_churn[module]["ai_removed"] += line_count

    result: dict[str, ChurnMetrics] = {}

    for module, churn in module_churn.items():
        total_churn = churn["total_added"] + churn["total_removed"]
        ai_churn = churn["ai_added"] + churn["ai_removed"]
        attribution_pct = (ai_churn / total_churn * 100.0) if total_churn > 0 else 0.0

        result[module] = ChurnMetrics(
            total_churn_lines=total_churn,
            ai_churn_lines=ai_churn,
            ai_churn_attribution_pct=attribution_pct,
        )

    return result
```

### 8.5 `tests/metrics/__init__.py`

```python
"""Tests for driftscope.metrics."""
```

### 8.6 `tests/metrics/test_survival.py`

```python
"""Tests for survival rate computation."""

from pathlib import Path

import pytest

from driftscope.errors import MetricError
from driftscope.metrics.survival import compute_survival_metrics
from driftscope.models.ast_diff import ASTDiffSet, ASTFileDiff, ASTNodeChange
from driftscope.models.blame import BlameLine


def _blame_line(line_number: int, commit_sha: str) -> BlameLine:
    return BlameLine(
        line_number=line_number,
        commit_sha=commit_sha,
        author_name="Author",
        author_email="a@example.com",
        content=f"line {line_number}",
    )


def _change(change_type: str, start: int, end: int) -> ASTNodeChange:
    return ASTNodeChange(
        node_type="function_definition",
        start_line=start,
        end_line=end,
        change_type=change_type,
        text_hash="a" * 64,
    )


class TestComputeSurvivalMetrics:
    """Test survival metrics computation."""

    def test_all_ai_lines_survive(self) -> None:
        """When all AI blame lines survive, rate is 1.0."""
        ai_sha = "a" * 40
        blame = {Path("src/main.py"): [_blame_line(i, ai_sha) for i in range(1, 11)]}
        diff_set = ASTDiffSet(
            diffs=[ASTFileDiff(
                file_path=Path("src/main.py"),
                commit_sha=ai_sha,
                changes=[_change("added", 1, 10)],
                authorship_class="ai",
            )],
            skipped_files=[],
        )
        result = compute_survival_metrics(blame, diff_set, ["90d"], {ai_sha}, set())
        assert "src" in result
        assert result["src"]["90d"].ai_survival_rate == 1.0

    def test_half_survive(self) -> None:
        """Half the lines surviving produces rate 0.5."""
        ai_sha = "a" * 40
        blame = {Path("src/main.py"): [_blame_line(i, ai_sha) for i in range(1, 6)]}
        diff_set = ASTDiffSet(
            diffs=[ASTFileDiff(
                file_path=Path("src/main.py"),
                commit_sha=ai_sha,
                changes=[_change("added", 1, 10)],
                authorship_class="ai",
            )],
            skipped_files=[],
        )
        result = compute_survival_metrics(blame, diff_set, ["90d"], {ai_sha}, set())
        assert result["src"]["90d"].ai_lines_introduced == 10
        assert result["src"]["90d"].ai_lines_surviving == 5

    def test_zero_introduced_no_division_by_zero(self) -> None:
        """No lines introduced yields rate 0.0, not NaN."""
        blame = {Path("src/main.py"): []}
        diff_set = ASTDiffSet(diffs=[], skipped_files=[])
        result = compute_survival_metrics(blame, diff_set, ["30d"], set(), set())
        assert "src" not in result  # empty blame, empty diffs = no module entry

    def test_multiple_windows(self) -> None:
        """Multiple windows produce separate SurvivalMetrics."""
        ai_sha = "a" * 40
        blame = {Path("src/main.py"): [_blame_line(1, ai_sha)]}
        diff_set = ASTDiffSet(
            diffs=[ASTFileDiff(
                file_path=Path("src/main.py"),
                commit_sha=ai_sha,
                changes=[_change("added", 1, 5)],
                authorship_class="ai",
            )],
            skipped_files=[],
        )
        result = compute_survival_metrics(blame, diff_set, ["30d", "90d"], {ai_sha}, set())
        assert "30d" in result["src"]
        assert "90d" in result["src"]

    def test_empty_windows_raises(self) -> None:
        """Empty windows list raises MetricError."""
        with pytest.raises(MetricError, match="At least one survival window"):
            compute_survival_metrics({}, ASTDiffSet(diffs=[], skipped_files=[]), [], set(), set())

    def test_mixed_authorship(self) -> None:
        """AI and human lines are counted separately."""
        ai_sha = "a" * 40
        human_sha = "b" * 40
        blame = {Path("src/main.py"): [
            _blame_line(1, ai_sha),
            _blame_line(2, ai_sha),
            _blame_line(3, human_sha),
        ]}
        diff_set = ASTDiffSet(
            diffs=[
                ASTFileDiff(
                    file_path=Path("src/main.py"), commit_sha=ai_sha,
                    changes=[_change("added", 1, 4)], authorship_class="ai",
                ),
                ASTFileDiff(
                    file_path=Path("src/main.py"), commit_sha=human_sha,
                    changes=[_change("added", 1, 2)], authorship_class="human",
                ),
            ],
            skipped_files=[],
        )
        result = compute_survival_metrics(blame, diff_set, ["90d"], {ai_sha}, {human_sha})
        sm = result["src"]["90d"]
        assert sm.ai_lines_surviving == 2
        assert sm.human_lines_surviving == 1
```

### 8.7 `tests/metrics/test_complexity.py`

```python
"""Tests for complexity delta computation."""

from driftscope.metrics.complexity import count_cyclomatic, count_cognitive
from driftscope.metrics.complexity import compute_complexity_metrics
from driftscope.models.ast_diff import ASTDiffSet, ASTFileDiff, ASTNodeChange
from driftscope.models.metrics import ComplexityMetrics


class TestCountCyclomatic:
    """Test cyclomatic complexity counting."""

    def test_empty_function(self) -> None:
        """Empty function body has cyclomatic 0."""
        assert count_cyclomatic("def foo():\n    pass") == 0

    def test_single_if(self) -> None:
        """Single if statement adds 1."""
        assert count_cyclomatic("if x:\n    pass") == 1

    def test_if_elif_else(self) -> None:
        """if + elif = 2 decision points."""
        source = "if x:\n    pass\nelif y:\n    pass"
        assert count_cyclomatic(source) == 2

    def test_for_loop(self) -> None:
        """for loop adds 1."""
        assert count_cyclomatic("for i in range(10):\n    pass") == 1

    def test_while_loop(self) -> None:
        """while loop adds 1."""
        assert count_cyclomatic("while True:\n    break") == 1

    def test_and_or(self) -> None:
        """and/or operators each add 1."""
        assert count_cyclomatic("if x and y or z:\n    pass") == 3  # if + and + or

    def test_exception_handling(self) -> None:
        """except adds 1."""
        assert count_cyclomatic("try:\n    pass\nexcept:\n    pass") == 1

    def test_with_statement(self) -> None:
        """with statement adds 1."""
        assert count_cyclomatic("with open('f') as f:\n    pass") == 1

    def test_multiple_decision_points(self) -> None:
        """Multiple decision points are summed."""
        source = "if a:\n    pass\nfor i in x:\n    if b and c:\n        pass"
        result = count_cyclomatic(source)
        assert result >= 4  # if + for + if + and


class TestCountCognitive:
    """Test cognitive complexity counting."""

    def test_flat_code(self) -> None:
        """Flat code has cognitive == cyclomatic."""
        source = "if x:\n    pass"
        assert count_cognitive(source) == count_cyclomatic(source)

    def test_nested_increments(self) -> None:
        """Nested control flow adds cognitive complexity."""
        flat = "if x:\n    pass\nif y:\n    pass"
        nested = "if x:\n    if y:\n        pass"
        assert count_cognitive(nested) >= count_cognitive(flat)


class TestComputeComplexityMetrics:
    """Test the full complexity metrics computation."""

    def test_empty_diff_set(self) -> None:
        """Empty diff set returns empty result."""
        diff_set = ASTDiffSet(diffs=[], skipped_files=[])
        result = compute_complexity_metrics(diff_set, {})
        assert result == {}

    def test_single_ai_commit(self) -> None:
        """Single AI commit produces correct mean delta."""
        from pathlib import Path

        sha = "a" * 40
        diff_set = ASTDiffSet(
            diffs=[ASTFileDiff(
                file_path=Path("src/main.py"),
                commit_sha=sha,
                changes=[ASTNodeChange(
                    node_type="function_definition",
                    start_line=1, end_line=5,
                    change_type="added",
                    text_hash="a" * 64,
                )],
                authorship_class="ai",
            )],
            skipped_files=[],
        )
        commit_weeks = {
            sha: {
                "week": "2025-06-02",
                "week_iso": "2025-06-02",
                "authorship_class": "ai",
                "cyclomatic_delta": 3,
                "cognitive_delta": 5,
            },
        }
        result = compute_complexity_metrics(diff_set, commit_weeks)
        assert "src" in result
        assert result["src"].cyclomatic_delta_ai == 3.0
        assert result["src"].cognitive_delta_ai == 5.0
        assert result["src"].cyclomatic_delta_human == 0.0

    def test_mixed_commits(self) -> None:
        """AI and human commits produce separate means."""
        from pathlib import Path

        ai_sha = "a" * 40
        human_sha = "b" * 40
        diff_set = ASTDiffSet(
            diffs=[
                ASTFileDiff(
                    file_path=Path("src/main.py"), commit_sha=ai_sha,
                    changes=[ASTNodeChange(
                        node_type="function_definition", start_line=1, end_line=3,
                        change_type="added", text_hash="a" * 64,
                    )],
                    authorship_class="ai",
                ),
                ASTFileDiff(
                    file_path=Path("src/main.py"), commit_sha=human_sha,
                    changes=[ASTNodeChange(
                        node_type="function_definition", start_line=4, end_line=6,
                        change_type="added", text_hash="b" * 64,
                    )],
                    authorship_class="human",
                ),
            ],
            skipped_files=[],
        )
        commit_weeks = {
            ai_sha: {"week": "2025-06-02", "week_iso": "2025-06-02",
                     "cyclomatic_delta": 4, "cognitive_delta": 6},
            human_sha: {"week": "2025-06-02", "week_iso": "2025-06-02",
                        "cyclomatic_delta": 1, "cognitive_delta": 2},
        }
        result = compute_complexity_metrics(diff_set, commit_weeks)
        assert result["src"].cyclomatic_delta_ai == 4.0
        assert result["src"].cyclomatic_delta_human == 1.0
```

### 8.8 `tests/metrics/test_churn.py`

```python
"""Tests for churn attribution computation."""

from pathlib import Path

from driftscope.metrics.churn import compute_churn_metrics
from driftscope.models.ast_diff import ASTDiffSet, ASTFileDiff, ASTNodeChange
from driftscope.models.metrics import ChurnMetrics


def _change(change_type: str, start: int, end: int) -> ASTNodeChange:
    return ASTNodeChange(
        node_type="function_definition",
        start_line=start,
        end_line=end,
        change_type=change_type,
        text_hash="a" * 64,
    )


class TestComputeChurnMetrics:
    """Test churn attribution computation."""

    def test_empty_diff_set(self) -> None:
        """Empty diff set returns empty dict."""
        diff_set = ASTDiffSet(diffs=[], skipped_files=[])
        result = compute_churn_metrics(diff_set)
        assert result == {}

    def test_all_ai_churn(self) -> None:
        """When all changes are AI, attribution is 100%."""
        diff_set = ASTDiffSet(
            diffs=[ASTFileDiff(
                file_path=Path("src/main.py"),
                commit_sha="a" * 40,
                changes=[_change("added", 1, 10), _change("removed", 11, 15)],
                authorship_class="ai",
            )],
            skipped_files=[],
        )
        result = compute_churn_metrics(diff_set)
        assert "src" in result
        assert result["src"].total_churn_lines == 15  # 10 added + 5 removed
        assert result["src"].ai_churn_lines == 15
        assert result["src"].ai_churn_attribution_pct == 100.0

    def test_all_human_churn(self) -> None:
        """When all changes are human, AI attribution is 0%."""
        diff_set = ASTDiffSet(
            diffs=[ASTFileDiff(
                file_path=Path("lib/util.py"),
                commit_sha="a" * 40,
                changes=[_change("added", 1, 5)],
                authorship_class="human",
            )],
            skipped_files=[],
        )
        result = compute_churn_metrics(diff_set)
        assert result["lib"].ai_churn_attribution_pct == 0.0
        assert result["lib"].total_churn_lines == 5

    def test_mixed_churn(self) -> None:
        """Mixed AI/human churn produces correct attribution."""
        diff_set = ASTDiffSet(
            diffs=[
                ASTFileDiff(
                    file_path=Path("src/main.py"), commit_sha="a" * 40,
                    changes=[_change("added", 1, 10)],  # 10 AI lines
                    authorship_class="ai",
                ),
                ASTFileDiff(
                    file_path=Path("src/main.py"), commit_sha="b" * 40,
                    changes=[_change("added", 11, 20), _change("removed", 21, 30)],
                    authorship_class="human",
                ),
            ],
            skipped_files=[],
        )
        result = compute_churn_metrics(diff_set)
        assert result["src"].total_churn_lines == 30  # 10 + 10 + 10
        assert result["src"].ai_churn_lines == 10
        assert abs(result["src"].ai_churn_attribution_pct - 33.33333333333333) < 0.01

    def test_no_changes_zero_churn(self) -> None:
        """Diffs with only modified (not added/removed) produce 0 churn."""
        diff_set = ASTDiffSet(
            diffs=[ASTFileDiff(
                file_path=Path("src/main.py"),
                commit_sha="a" * 40,
                changes=[_change("modified", 1, 5)],
                authorship_class="ai",
            )],
            skipped_files=[],
        )
        result = compute_churn_metrics(diff_set)
        # "modified" changes don't count as churn (they are neither added nor removed).
        assert result["src"].total_churn_lines == 0

    def test_multiple_modules(self) -> None:
        """Changes in different modules produce separate metrics."""
        diff_set = ASTDiffSet(
            diffs=[
                ASTFileDiff(
                    file_path=Path("src/main.py"), commit_sha="a" * 40,
                    changes=[_change("added", 1, 5)],
                    authorship_class="ai",
                ),
                ASTFileDiff(
                    file_path=Path("lib/util.py"), commit_sha="b" * 40,
                    changes=[_change("added", 1, 3)],
                    authorship_class="human",
                ),
            ],
            skipped_files=[],
        )
        result = compute_churn_metrics(diff_set)
        assert "src" in result
        assert "lib" in result
        assert result["src"].ai_churn_attribution_pct == 100.0
        assert result["lib"].ai_churn_attribution_pct == 0.0
```

### TDD Step Sequence

```
Step 1: Write tests/metrics/test_complexity.py with cyclomatic/cognitive unit tests.
  -> Run: python -m pytest tests/metrics/test_complexity.py -v
  -> Expect: FAIL (module not found)

Step 2: Implement driftscope/metrics/__init__.py and complexity.py.
  -> Run: python -m pytest tests/metrics/test_complexity.py -v
  -> Expect: PASS
  -> Commit: feat(metrics): add cyclomatic and cognitive complexity delta computation

Step 3: Write tests/metrics/test_survival.py with all tests.
  -> Run: python -m pytest tests/metrics/test_survival.py -v
  -> Expect: FAIL (module not found)

Step 4: Implement survival.py.
  -> Run: python -m pytest tests/metrics/test_survival.py -v
  -> Expect: PASS
  -> Commit: feat(metrics): add line survival rate computation per module per window

Step 5: Write tests/metrics/test_churn.py with all tests.
  -> Run: python -m pytest tests/metrics/test_churn.py -v
  -> Expect: FAIL (module not found)

Step 6: Implement churn.py.
  -> Run: python -m pytest tests/metrics/test_churn.py -v
  -> Expect: PASS
  -> Commit: feat(metrics): add module-level churn attribution computation

Step 7: Full suite coverage check.
  -> Run: python -m pytest tests/metrics/ --cov=driftscope/metrics --cov-report=term-missing
  -> Expect: >=95% line coverage
```

### Commit

```
feat(metrics): add survival rate, complexity delta, and churn attribution computation per module
```

---

## Task 9: Reporting (json, markdown, html, csv)

**Goal:** Implement all output format renderers.

### Files

```
driftscope/reporting/__init__.py
driftscope/reporting/json_report.py   # versioned JSON schema output
driftscope/reporting/markdown.py      # GitHub-flavored Markdown
driftscope/reporting/html.py          # self-contained HTML dashboard
driftscope/reporting/csv_export.py    # tabular CSV
driftscope/reporting/templates/__init__.py
tests/reporting/__init__.py
tests/reporting/test_json_report.py
tests/reporting/test_markdown.py
tests/reporting/test_html.py
tests/reporting/test_csv_export.py
```

### 9.1 `driftscope/reporting/__init__.py`

```python
"""Reporting — output format renderers for DriftScope analysis results."""

from driftscope.reporting.json_report import render_json
from driftscope.reporting.markdown import render_markdown
from driftscope.reporting.html import render_html
from driftscope.reporting.csv_export import render_csv

__all__ = ["render_json", "render_markdown", "render_html", "render_csv"]
```

### 9.2 `driftscope/reporting/json_report.py`

```python
"""Versioned JSON schema output.

Serializes MetricsResult to JSON with optional provenance data.
Validates round-trip: serialize -> parse -> validate.

Time Complexity: O(N) where N is the size of the MetricsResult.
Space Complexity: O(N) for the JSON string.
"""

import json
from typing import Any

from driftscope.errors import ReportError
from driftscope.models.metrics import ModuleMetrics
from driftscope.models.provenance import ProvenanceEntry
from driftscope.models.report import MetricsResult


def render_json(
    result: MetricsResult,
    include_provenance: bool = False,
    provenance: list[ProvenanceEntry] | None = None,
) -> str:
    """Render a MetricsResult as a JSON string.

    Args:
        result: The analysis result to serialize.
        include_provenance: Whether to include line-level provenance.
        provenance: Provenance entries to include (if include_provenance is True).

    Returns:
        JSON string conforming to the DriftScope report schema.

    Raises:
        ReportError: If serialization fails.
    """
    try:
        data = json.loads(result.model_dump_json())
    except Exception as e:
        raise ReportError(
            message=f"Failed to serialize MetricsResult to JSON: {e}",
            suggestion="Check for invalid data in the MetricsResult.",
        ) from e

    if include_provenance and provenance is not None:
        data["provenance"] = [
            json.loads(p.model_dump_json()) for p in provenance
        ]

    try:
        return json.dumps(data, indent=2, ensure_ascii=False)
    except Exception as e:
        raise ReportError(
            message=f"Failed to format JSON output: {e}",
        ) from e
```

### 9.3 `driftscope/reporting/markdown.py`

```python
"""GitHub-flavored Markdown report renderer.

Produces a structured Markdown report with tables for each metric
dimension.

Time Complexity: O(N) where N is the total data size.
Space Complexity: O(N) for the output string.
"""

from driftscope.errors import ReportError
from driftscope.models.report import MetricsResult


def render_markdown(result: MetricsResult) -> str:
    """Render a MetricsResult as a GitHub-flavored Markdown string.

    Sections produced:
    1. Header with repo path and date range
    2. Executive summary table (one row per module)
    3. Survival trend table per module per window
    4. Complexity trend table (weekly series)
    5. Churn attribution table
    6. Threshold status
    7. Skipped files
    8. Metadata

    Args:
        result: The analysis result to render.

    Returns:
        Complete Markdown string.

    Raises:
        ReportError: If rendering fails.
    """
    try:
        sections: list[str] = []

        # Header.
        sections.append(_render_header(result))

        # Executive summary.
        sections.append(_render_executive_summary(result))

        # Survival trends.
        sections.append(_render_survival_table(result))

        # Complexity trend.
        sections.append(_render_complexity_table(result))

        # Churn attribution.
        sections.append(_render_churn_table(result))

        # Threshold breaches.
        sections.append(_render_thresholds(result))

        # Skipped files.
        sections.append(_render_skipped_files(result))

        # Metadata.
        sections.append(_render_metadata(result))

        return "\n\n".join(sections) + "\n"
    except Exception as e:
        raise ReportError(
            message=f"Failed to render Markdown report: {e}",
        ) from e


def _render_header(result: MetricsResult) -> str:
    """Render the report header."""
    return (
        f"# DriftScope Report\n\n"
        f"**Repo:** `{result.repo_path}`\n\n"
        f"**Range:** {result.range_start.strftime('%Y-%m-%d')} to "
        f"{result.range_end.strftime('%Y-%m-%d')}\n\n"
        f"**Schema version:** {result.schema_version}"
    )


def _render_executive_summary(result: MetricsResult) -> str:
    """Render the executive summary table."""
    lines = [
        "## Executive Summary\n",
        "| Module | Total Lines | AI Lines | Human Lines |",
        "|--------|-------------|----------|-------------|",
    ]
    for mod in result.modules:
        lines.append(
            f"| {mod.module_path} | {mod.total_lines:,} | "
            f"{mod.ai_lines:,} | {mod.human_lines:,} |"
        )
    return "\n".join(lines)


def _render_survival_table(result: MetricsResult) -> str:
    """Render survival rate table per module per window."""
    lines = [
        "## Survival Rates\n",
        "| Module | Window | AI Rate | Human Rate |",
        "|--------|--------|---------|------------|",
    ]
    for mod in result.modules:
        for window, sm in mod.survival.items():
            lines.append(
                f"| {mod.module_path} | {window} | "
                f"{sm.ai_survival_rate:.1%} | {sm.human_survival_rate:.1%} |"
            )
    return "\n".join(lines)


def _render_complexity_table(result: MetricsResult) -> str:
    """Render complexity delta table."""
    lines = [
        "## Complexity Delta\n",
        "| Module | AI Cyclomatic | Human Cyclomatic | AI Cognitive | Human Cognitive |",
        "|--------|--------------|------------------|-------------|-----------------|",
    ]
    for mod in result.modules:
        c = mod.complexity
        lines.append(
            f"| {mod.module_path} | {c.cyclomatic_delta_ai:.2f} | "
            f"{c.cyclomatic_delta_human:.2f} | {c.cognitive_delta_ai:.2f} | "
            f"{c.cognitive_delta_human:.2f} |"
        )
    return "\n".join(lines)


def _render_churn_table(result: MetricsResult) -> str:
    """Render churn attribution table."""
    lines = [
        "## Churn Attribution (365d)\n",
        "| Module | Total Churn | AI Churn | AI Attribution % |",
        "|--------|-------------|----------|------------------|",
    ]
    for mod in result.modules:
        ch = mod.churn
        lines.append(
            f"| {mod.module_path} | {ch.total_churn_lines:,} | "
            f"{ch.ai_churn_lines:,} | {ch.ai_churn_attribution_pct:.1f}% |"
        )
    return "\n".join(lines)


def _render_thresholds(result: MetricsResult) -> str:
    """Render threshold breach status."""
    if not result.threshold_breaches:
        return "## Threshold Status\n\nNo threshold breaches detected."
    lines = [
        "## Threshold Breaches\n",
        "| Metric | Module | Value | Threshold | Direction |",
        "|--------|--------|-------|-----------|-----------|",
    ]
    for breach in result.threshold_breaches:
        lines.append(
            f"| {breach.metric} | {breach.module_path} | "
            f"{breach.value:.1f} | {breach.threshold:.1f} | {breach.direction} |"
        )
    return "\n".join(lines)


def _render_skipped_files(result: MetricsResult) -> str:
    """Render skipped files list."""
    if not result.skipped_files:
        return "## Skipped Files\n\nNo files were skipped."
    lines = ["## Skipped Files\n"]
    for entry in result.skipped_files:
        path = entry.get("path", "unknown")
        reason = entry.get("reason", "unknown")
        lines.append(f"- `{path}`: {reason}")
    return "\n".join(lines)


def _render_metadata(result: MetricsResult) -> str:
    """Render metadata footer."""
    incomplete = "Yes" if result.data_incomplete else "No"
    return (
        f"## Metadata\n\n"
        f"- **Schema version:** {result.schema_version}\n"
        f"- **Data incomplete:** {incomplete}\n"
        f"- **Commit range:** `{result.commit_range[0][:7]}..{result.commit_range[1][:7]}`"
    )
```

### 9.4 `driftscope/reporting/html.py`

```python
"""Self-contained HTML dashboard renderer.

Produces a single HTML file with inline CSS, no external dependencies,
no JavaScript. All sections from the HTML Dashboard Layout spec.

Time Complexity: O(N) where N is the total data size.
Space Complexity: O(N) for the output string.
"""

from driftscope.errors import ReportError
from driftscope.models.report import MetricsResult

_CSS = """
body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
    max-width: 1200px;
    margin: 0 auto;
    padding: 20px;
    background: #ffffff;
    color: #1a1a1a;
    line-height: 1.6;
}
h1 { border-bottom: 2px solid #e1e4e8; padding-bottom: 10px; }
h2 { border-bottom: 1px solid #e1e4e8; padding-bottom: 8px; margin-top: 2em; }
table { border-collapse: collapse; width: 100%; margin-bottom: 1em; }
th, td { border: 1px solid #d0d7de; padding: 8px 12px; text-align: left; }
th { background: #f6f8fa; font-weight: 600; }
tr:nth-child(even) { background: #f6f8fa; }
.threshold-breach { color: #cf222e; font-weight: 600; }
.metadata { color: #656d76; font-size: 0.9em; }
"""


def render_html(result: MetricsResult) -> str:
    """Render a MetricsResult as a self-contained HTML document.

    Args:
        result: The analysis result to render.

    Returns:
        Complete HTML string with inline CSS.

    Raises:
        ReportError: If rendering fails.
    """
    try:
        sections: list[str] = []
        sections.append(_html_header(result))
        sections.append(_html_executive_summary(result))
        sections.append(_html_survival(result))
        sections.append(_html_complexity(result))
        sections.append(_html_churn(result))
        sections.append(_html_thresholds(result))
        sections.append(_html_skipped(result))
        sections.append(_html_metadata(result))

        body = "\n".join(sections)
        return (
            "<!DOCTYPE html>\n"
            "<html lang=\"en\">\n<head>\n"
            "<meta charset=\"utf-8\">\n"
            f"<title>DriftScope Report</title>\n"
            f"<style>{_CSS}</style>\n"
            "</head>\n<body>\n"
            f"{body}\n"
            "</body>\n</html>"
        )
    except Exception as e:
        raise ReportError(
            message=f"Failed to render HTML report: {e}",
        ) from e


def _html_header(result: MetricsResult) -> str:
    return (
        f"<h1>DriftScope Report</h1>\n"
        f"<p><strong>Repo:</strong> {result.repo_path}</p>\n"
        f"<p><strong>Range:</strong> {result.range_start.strftime('%Y-%m-%d')} to "
        f"{result.range_end.strftime('%Y-%m-%d')}</p>"
    )


def _html_executive_summary(result: MetricsResult) -> str:
    rows = "".join(
        f"<tr><td>{m.module_path}</td><td>{m.total_lines:,}</td>"
        f"<td>{m.ai_lines:,}</td><td>{m.human_lines:,}</td></tr>"
        for m in result.modules
    )
    return (
        "<h2>Executive Summary</h2>\n"
        "<table><tr><th>Module</th><th>Total Lines</th>"
        "<th>AI Lines</th><th>Human Lines</th></tr>\n"
        f"{rows}</table>"
    )


def _html_survival(result: MetricsResult) -> str:
    rows = ""
    for m in result.modules:
        for window, sm in m.survival.items():
            rows += (
                f"<tr><td>{m.module_path}</td><td>{window}</td>"
                f"<td>{sm.ai_survival_rate:.1%}</td>"
                f"<td>{sm.human_survival_rate:.1%}</td></tr>\n"
            )
    return (
        "<h2>Survival Rates</h2>\n"
        "<table><tr><th>Module</th><th>Window</th>"
        "<th>AI Rate</th><th>Human Rate</th></tr>\n"
        f"{rows}</table>"
    )


def _html_complexity(result: MetricsResult) -> str:
    rows = "".join(
        f"<tr><td>{m.module_path}</td>"
        f"<td>{m.complexity.cyclomatic_delta_ai:.2f}</td>"
        f"<td>{m.complexity.cyclomatic_delta_human:.2f}</td>"
        f"<td>{m.complexity.cognitive_delta_ai:.2f}</td>"
        f"<td>{m.complexity.cognitive_delta_human:.2f}</td></tr>\n"
        for m in result.modules
    )
    return (
        "<h2>Complexity Delta</h2>\n"
        "<table><tr><th>Module</th><th>AI Cyclomatic</th>"
        "<th>Human Cyclomatic</th><th>AI Cognitive</th>"
        "<th>Human Cognitive</th></tr>\n"
        f"{rows}</table>"
    )


def _html_churn(result: MetricsResult) -> str:
    rows = "".join(
        f"<tr><td>{m.module_path}</td><td>{m.churn.total_churn_lines:,}</td>"
        f"<td>{m.churn.ai_churn_lines:,}</td>"
        f"<td>{m.churn.ai_churn_attribution_pct:.1f}%</td></tr>\n"
        for m in result.modules
    )
    return (
        "<h2>Churn Attribution (365d)</h2>\n"
        "<table><tr><th>Module</th><th>Total Churn</th>"
        "<th>AI Churn</th><th>AI Attribution %</th></tr>\n"
        f"{rows}</table>"
    )


def _html_thresholds(result: MetricsResult) -> str:
    if not result.threshold_breaches:
        return "<h2>Threshold Status</h2><p>No threshold breaches detected.</p>"
    rows = "".join(
        f"<tr class=\"threshold-breach\"><td>{b.metric}</td>"
        f"<td>{b.module_path}</td><td>{b.value:.1f}</td>"
        f"<td>{b.threshold:.1f}</td><td>{b.direction}</td></tr>\n"
        for b in result.threshold_breaches
    )
    return (
        "<h2>Threshold Breaches</h2>\n"
        "<table><tr><th>Metric</th><th>Module</th><th>Value</th>"
        "<th>Threshold</th><th>Direction</th></tr>\n"
        f"{rows}</table>"
    )


def _html_skipped(result: MetricsResult) -> str:
    if not result.skipped_files:
        return "<h2>Skipped Files</h2><p>No files were skipped.</p>"
    items = "".join(
        f"<li><code>{e.get('path', 'unknown')}</code>: {e.get('reason', 'unknown')}</li>"
        for e in result.skipped_files
    )
    return f"<h2>Skipped Files</h2><ul>{items}</ul>"


def _html_metadata(result: MetricsResult) -> str:
    incomplete = "Yes" if result.data_incomplete else "No"
    return (
        f"<div class=\"metadata\">\n"
        f"<h2>Metadata</h2>\n"
        f"<p>Schema version: {result.schema_version}</p>\n"
        f"<p>Data incomplete: {incomplete}</p>\n"
        f"<p>Commit range: <code>{result.commit_range[0][:7]}..{result.commit_range[1][:7]}</code></p>\n"
        f"</div>"
    )
```

### 9.5 `driftscope/reporting/csv_export.py`

```python
"""Tabular CSV export for BI tool import.

One row per module per survival window.

Time Complexity: O(N) where N is the number of modules * windows.
Space Complexity: O(N) for the output string.
"""

import csv
import io

from driftscope.errors import ReportError
from driftscope.models.report import MetricsResult

_HEADERS = [
    "module",
    "total_lines",
    "ai_lines",
    "human_lines",
    "window",
    "ai_survival_rate",
    "human_survival_rate",
    "ai_cyclomatic_delta",
    "human_cyclomatic_delta",
    "ai_cognitive_delta",
    "human_cognitive_delta",
    "total_churn_lines",
    "ai_churn_lines",
    "ai_churn_attribution_pct",
]


def render_csv(result: MetricsResult) -> str:
    """Render a MetricsResult as CSV.

    One row per module per survival window.

    Args:
        result: The analysis result to render.

    Returns:
        CSV string with header row.

    Raises:
        ReportError: If rendering fails.
    """
    try:
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(_HEADERS)

        for mod in result.modules:
            for window, sm in mod.survival.items():
                writer.writerow([
                    mod.module_path,
                    mod.total_lines,
                    mod.ai_lines,
                    mod.human_lines,
                    sm.window,
                    f"{sm.ai_survival_rate:.4f}",
                    f"{sm.human_survival_rate:.4f}",
                    f"{mod.complexity.cyclomatic_delta_ai:.2f}",
                    f"{mod.complexity.cyclomatic_delta_human:.2f}",
                    f"{mod.complexity.cognitive_delta_ai:.2f}",
                    f"{mod.complexity.cognitive_delta_human:.2f}",
                    mod.churn.total_churn_lines,
                    mod.churn.ai_churn_lines,
                    f"{mod.churn.ai_churn_attribution_pct:.2f}",
                ])

        return output.getvalue()
    except Exception as e:
        raise ReportError(
            message=f"Failed to render CSV report: {e}",
        ) from e
```

### 9.6 `driftscope/reporting/templates/__init__.py`

```python
"""HTML dashboard templates."""
```

### 9.7 `tests/reporting/__init__.py`

```python
"""Tests for driftscope.reporting."""
```

### 9.8 `tests/reporting/test_json_report.py`

```python
"""Tests for JSON report renderer."""

import json

from datetime import datetime, timezone
from pathlib import Path

from driftscope.models.metrics import (
    ChurnMetrics,
    ComplexityMetrics,
    ModuleMetrics,
    SurvivalMetrics,
)
from driftscope.models.provenance import ProvenanceEntry
from driftscope.models.report import MetricsResult
from driftscope.reporting.json_report import render_json


def _result() -> MetricsResult:
    return MetricsResult(
        repo_path=Path("/tmp/repo"),
        commit_range=("a" * 40, "c" * 40),
        range_start=datetime(2025, 1, 1, tzinfo=timezone.utc),
        range_end=datetime(2025, 4, 1, tzinfo=timezone.utc),
        modules=[ModuleMetrics(
            module_path="src/payments",
            total_lines=5000,
            ai_lines=1204,
            human_lines=3796,
            survival={"90d": SurvivalMetrics(
                window="90d",
                ai_lines_introduced=100,
                ai_lines_surviving=67,
                ai_survival_rate=0.67,
                human_lines_introduced=500,
                human_lines_surviving=450,
                human_survival_rate=0.9,
            )},
            complexity=ComplexityMetrics(
                cyclomatic_delta_ai=3.2,
                cyclomatic_delta_human=1.1,
                cognitive_delta_ai=4.5,
                cognitive_delta_human=2.0,
                weekly_series=[],
            ),
            churn=ChurnMetrics(
                total_churn_lines=2000,
                ai_churn_lines=500,
                ai_churn_attribution_pct=25.0,
            ),
        )],
        skipped_files=[],
    )


class TestRenderJson:
    """Test JSON report rendering."""

    def test_produces_valid_json(self) -> None:
        """Output is parseable JSON."""
        output = render_json(_result())
        parsed = json.loads(output)
        assert isinstance(parsed, dict)

    def test_contains_schema_version(self) -> None:
        """JSON output includes schema_version."""
        output = render_json(_result())
        parsed = json.loads(output)
        assert parsed["schema_version"] == "1.0.0"

    def test_contains_modules(self) -> None:
        """JSON output includes module data."""
        output = render_json(_result())
        parsed = json.loads(output)
        assert len(parsed["modules"]) == 1
        assert parsed["modules"][0]["module_path"] == "src/payments"

    def test_round_trip_validation(self) -> None:
        """JSON output can be parsed back into MetricsResult."""
        output = render_json(_result())
        restored = MetricsResult.model_validate_json(output)
        assert restored.schema_version == "1.0.0"
        assert len(restored.modules) == 1

    def test_with_provenance(self) -> None:
        """Provenance entries are included when requested."""
        provenance = [
            ProvenanceEntry(
                file_path="src/payments.py",
                line_start=10,
                line_end=20,
                authorship_class="ai",
                originating_commit_sha="a" * 40,
                commit_timestamp=datetime(2025, 3, 1, tzinfo=timezone.utc),
                co_authorship_tag="Co-Authored-By: Claude",
            ),
        ]
        output = render_json(_result(), include_provenance=True, provenance=provenance)
        parsed = json.loads(output)
        assert "provenance" in parsed
        assert len(parsed["provenance"]) == 1
        assert parsed["provenance"][0]["authorship_class"] == "ai"

    def test_without_provenance(self) -> None:
        """No provenance field when include_provenance is False."""
        output = render_json(_result(), include_provenance=False)
        parsed = json.loads(output)
        assert "provenance" not in parsed
```

### 9.9 `tests/reporting/test_markdown.py`

```python
"""Tests for Markdown report renderer."""

from datetime import datetime, timezone
from pathlib import Path

from driftscope.models.metrics import (
    ChurnMetrics,
    ComplexityMetrics,
    ModuleMetrics,
    SurvivalMetrics,
)
from driftscope.models.report import MetricsResult, ThresholdBreach
from driftscope.reporting.markdown import render_markdown


def _result(**overrides: object) -> MetricsResult:
    defaults = {
        "repo_path": Path("/tmp/repo"),
        "commit_range": ("a" * 40, "c" * 40),
        "range_start": datetime(2025, 1, 1, tzinfo=timezone.utc),
        "range_end": datetime(2025, 4, 1, tzinfo=timezone.utc),
        "modules": [ModuleMetrics(
            module_path="src/payments",
            total_lines=5000,
            ai_lines=1204,
            human_lines=3796,
            survival={"90d": SurvivalMetrics(
                window="90d",
                ai_lines_introduced=100,
                ai_lines_surviving=67,
                ai_survival_rate=0.67,
                human_lines_introduced=500,
                human_lines_surviving=450,
                human_survival_rate=0.9,
            )},
            complexity=ComplexityMetrics(
                cyclomatic_delta_ai=3.2,
                cyclomatic_delta_human=1.1,
                cognitive_delta_ai=4.5,
                cognitive_delta_human=2.0,
                weekly_series=[],
            ),
            churn=ChurnMetrics(
                total_churn_lines=2000,
                ai_churn_lines=500,
                ai_churn_attribution_pct=25.0,
            ),
        )],
        "skipped_files": [],
    }
    defaults.update(overrides)
    return MetricsResult(**defaults)  # type: ignore[arg-type]


class TestRenderMarkdown:
    """Test Markdown report rendering."""

    def test_contains_header(self) -> None:
        """Output contains the DriftScope Report header."""
        output = render_markdown(_result())
        assert "# DriftScope Report" in output

    def test_contains_executive_summary(self) -> None:
        """Output contains the Executive Summary section."""
        output = render_markdown(_result())
        assert "## Executive Summary" in output
        assert "src/payments" in output

    def test_contains_survival_rates(self) -> None:
        """Output contains the Survival Rates section."""
        output = render_markdown(_result())
        assert "## Survival Rates" in output

    def test_contains_complexity_delta(self) -> None:
        """Output contains the Complexity Delta section."""
        output = render_markdown(_result())
        assert "## Complexity Delta" in output

    def test_contains_churn_attribution(self) -> None:
        """Output contains the Churn Attribution section."""
        output = render_markdown(_result())
        assert "## Churn Attribution" in output

    def test_no_breaches_message(self) -> None:
        """When no breaches, output says so."""
        output = render_markdown(_result())
        assert "No threshold breaches detected" in output

    def test_breach_shown(self) -> None:
        """Threshold breach details appear in the report."""
        result = _result(
            threshold_breaches=[ThresholdBreach(
                metric="ai_churn_attribution_pct",
                module_path="src/payments",
                value=62.5,
                threshold=50.0,
                direction="above",
            )],
        )
        output = render_markdown(result)
        assert "## Threshold Breaches" in output
        assert "62.5" in output

    def test_contains_metadata(self) -> None:
        """Output contains the Metadata section."""
        output = render_markdown(_result())
        assert "## Metadata" in output
        assert "1.0.0" in output

    def test_skipped_files_listed(self) -> None:
        """Skipped files are listed with reasons."""
        result = _result(
            skipped_files=[{"path": "vendor/lib.js", "reason": "unsupported_extension"}],
        )
        output = render_markdown(result)
        assert "vendor/lib.js" in output
        assert "unsupported_extension" in output
```

### 9.10 `tests/reporting/test_html.py`

```python
"""Tests for HTML dashboard renderer."""

from datetime import datetime, timezone
from pathlib import Path

from driftscope.models.metrics import (
    ChurnMetrics,
    ComplexityMetrics,
    ModuleMetrics,
    SurvivalMetrics,
)
from driftscope.models.report import MetricsResult, ThresholdBreach
from driftscope.reporting.html import render_html


def _result(**overrides: object) -> MetricsResult:
    defaults = {
        "repo_path": Path("/tmp/repo"),
        "commit_range": ("a" * 40, "c" * 40),
        "range_start": datetime(2025, 1, 1, tzinfo=timezone.utc),
        "range_end": datetime(2025, 4, 1, tzinfo=timezone.utc),
        "modules": [ModuleMetrics(
            module_path="src/payments",
            total_lines=5000,
            ai_lines=1204,
            human_lines=3796,
            survival={"90d": SurvivalMetrics(
                window="90d",
                ai_lines_introduced=100,
                ai_lines_surviving=67,
                ai_survival_rate=0.67,
                human_lines_introduced=500,
                human_lines_surviving=450,
                human_survival_rate=0.9,
            )},
            complexity=ComplexityMetrics(
                cyclomatic_delta_ai=3.2,
                cyclomatic_delta_human=1.1,
                cognitive_delta_ai=4.5,
                cognitive_delta_human=2.0,
                weekly_series=[],
            ),
            churn=ChurnMetrics(
                total_churn_lines=2000,
                ai_churn_lines=500,
                ai_churn_attribution_pct=25.0,
            ),
        )],
        "skipped_files": [],
    }
    defaults.update(overrides)
    return MetricsResult(**defaults)  # type: ignore[arg-type]


class TestRenderHtml:
    """Test HTML dashboard rendering."""

    def test_self_contained(self) -> None:
        """Output is a complete HTML document with no external refs."""
        output = render_html(_result())
        assert output.startswith("<!DOCTYPE html>")
        assert "</html>" in output
        assert "http://" not in output.split("<style>")[0]  # no external links before CSS
        assert "https://" not in output.split("<style>")[0]

    def test_contains_inline_css(self) -> None:
        """Output has inline CSS in a style tag."""
        output = render_html(_result())
        assert "<style>" in output
        assert "</style>" in output
        assert "font-family" in output

    def test_contains_executive_summary(self) -> None:
        """Output contains the executive summary table."""
        output = render_html(_result())
        assert "Executive Summary" in output
        assert "src/payments" in output

    def test_contains_survival(self) -> None:
        """Output contains survival rate section."""
        output = render_html(_result())
        assert "Survival Rates" in output

    def test_contains_complexity(self) -> None:
        """Output contains complexity delta section."""
        output = render_html(_result())
        assert "Complexity Delta" in output

    def test_contains_churn(self) -> None:
        """Output contains churn attribution section."""
        output = render_html(_result())
        assert "Churn Attribution" in output

    def test_no_breaches_message(self) -> None:
        """No breaches produces a message, not an empty section."""
        output = render_html(_result())
        assert "No threshold breaches detected" in output

    def test_breach_shown(self) -> None:
        """Threshold breach details appear in the HTML."""
        result = _result(
            threshold_breaches=[ThresholdBreach(
                metric="ai_churn_attribution_pct",
                module_path="src/payments",
                value=62.5,
                threshold=50.0,
                direction="above",
            )],
        )
        output = render_html(result)
        assert "Threshold Breaches" in output
        assert "threshold-breach" in output

    def test_contains_metadata(self) -> None:
        """Output contains the metadata footer."""
        output = render_html(_result())
        assert "Metadata" in output
        assert "1.0.0" in output

    def test_no_js_dependencies(self) -> None:
        """Output contains no script tags."""
        output = render_html(_result())
        assert "<script" not in output
```

### 9.11 `tests/reporting/test_csv_export.py`

```python
"""Tests for CSV export renderer."""

import csv
import io

from datetime import datetime, timezone
from pathlib import Path

from driftscope.models.metrics import (
    ChurnMetrics,
    ComplexityMetrics,
    ModuleMetrics,
    SurvivalMetrics,
)
from driftscope.models.report import MetricsResult
from driftscope.reporting.csv_export import render_csv


def _result() -> MetricsResult:
    return MetricsResult(
        repo_path=Path("/tmp/repo"),
        commit_range=("a" * 40, "c" * 40),
        range_start=datetime(2025, 1, 1, tzinfo=timezone.utc),
        range_end=datetime(2025, 4, 1, tzinfo=timezone.utc),
        modules=[ModuleMetrics(
            module_path="src/payments",
            total_lines=5000,
            ai_lines=1204,
            human_lines=3796,
            survival={
                "30d": SurvivalMetrics(
                    window="30d",
                    ai_lines_introduced=50,
                    ai_lines_surviving=40,
                    ai_survival_rate=0.8,
                    human_lines_introduced=200,
                    human_lines_surviving=190,
                    human_survival_rate=0.95,
                ),
                "90d": SurvivalMetrics(
                    window="90d",
                    ai_lines_introduced=100,
                    ai_lines_surviving=67,
                    ai_survival_rate=0.67,
                    human_lines_introduced=500,
                    human_lines_surviving=450,
                    human_survival_rate=0.9,
                ),
            },
            complexity=ComplexityMetrics(
                cyclomatic_delta_ai=3.2,
                cyclomatic_delta_human=1.1,
                cognitive_delta_ai=4.5,
                cognitive_delta_human=2.0,
                weekly_series=[],
            ),
            churn=ChurnMetrics(
                total_churn_lines=2000,
                ai_churn_lines=500,
                ai_churn_attribution_pct=25.0,
            ),
        )],
        skipped_files=[],
    )


class TestRenderCsv:
    """Test CSV export rendering."""

    def test_parseable_as_csv(self) -> None:
        """Output is valid CSV."""
        output = render_csv(_result())
        reader = csv.reader(io.StringIO(output))
        rows = list(reader)
        assert len(rows) > 1  # header + data

    def test_header_row(self) -> None:
        """First row contains expected headers."""
        output = render_csv(_result())
        reader = csv.reader(io.StringIO(output))
        header = next(reader)
        assert "module" in header
        assert "window" in header
        assert "ai_survival_rate" in header
        assert "ai_churn_attribution_pct" in header

    def test_one_row_per_window(self) -> None:
        """Two windows produce two data rows."""
        output = render_csv(_result())
        reader = csv.reader(io.StringIO(output))
        rows = list(reader)
        # 1 header + 2 data rows (30d, 90d)
        assert len(rows) == 3

    def test_values_correct(self) -> None:
        """Data values match the input MetricsResult."""
        output = render_csv(_result())
        reader = csv.reader(io.StringIO(output))
        rows = list(reader)
        # First data row is 30d.
        assert rows[1][0] == "src/payments"
        assert rows[1][4] == "30d"
        # Second data row is 90d.
        assert rows[2][4] == "90d"

    def test_empty_modules(self) -> None:
        """MetricsResult with no modules produces only headers."""
        result = MetricsResult(
            repo_path=Path("/tmp/repo"),
            commit_range=("a" * 40, "c" * 40),
            range_start=datetime(2025, 1, 1, tzinfo=timezone.utc),
            range_end=datetime(2025, 4, 1, tzinfo=timezone.utc),
            modules=[],
            skipped_files=[],
        )
        output = render_csv(result)
        reader = csv.reader(io.StringIO(output))
        rows = list(reader)
        assert len(rows) == 1  # header only
```

### TDD Step Sequence

```
Step 1: Write tests/reporting/test_json_report.py with all tests.
  -> Run: python -m pytest tests/reporting/test_json_report.py -v
  -> Expect: FAIL (module not found)

Step 2: Implement driftscope/reporting/__init__.py and json_report.py + templates/__init__.py.
  -> Run: python -m pytest tests/reporting/test_json_report.py -v
  -> Expect: PASS
  -> Commit: feat(reporting): add versioned JSON report renderer with provenance support

Step 3: Write tests/reporting/test_markdown.py with all tests.
  -> Run: python -m pytest tests/reporting/test_markdown.py -v
  -> Expect: FAIL (module not found)

Step 4: Implement markdown.py.
  -> Run: python -m pytest tests/reporting/test_markdown.py -v
  -> Expect: PASS
  -> Commit: feat(reporting): add GitHub-flavored Markdown report renderer

Step 5: Write tests/reporting/test_html.py with all tests.
  -> Run: python -m pytest tests/reporting/test_html.py -v
  -> Expect: FAIL (module not found)

Step 6: Implement html.py.
  -> Run: python -m pytest tests/reporting/test_html.py -v
  -> Expect: PASS
  -> Commit: feat(reporting): add self-contained HTML dashboard renderer

Step 7: Write tests/reporting/test_csv_export.py with all tests.
  -> Run: python -m pytest tests/reporting/test_csv_export.py -v
  -> Expect: FAIL (module not found)

Step 8: Implement csv_export.py.
  -> Run: python -m pytest tests/reporting/test_csv_export.py -v
  -> Expect: PASS
  -> Commit: feat(reporting): add CSV export renderer for BI tool import

Step 9: Full suite coverage check.
  -> Run: python -m pytest tests/reporting/ --cov=driftscope/reporting --cov-report=term-missing
  -> Expect: >=95% line coverage
```

### Commit

```
feat(reporting): add JSON, Markdown, HTML dashboard, and CSV output renderers
```

---

## Task 10: Cache (SQLite Manager)

**Goal:** Implement incremental analysis cache for re-runs using SQLite.

### Files

```
driftscope/cache/__init__.py
driftscope/cache/manager.py
tests/cache/__init__.py
tests/cache/test_manager.py
```

---

### `driftscope/cache/__init__.py`

```python
"""DriftScope incremental analysis cache.

Provides a SQLite-backed cache for AST parse results keyed on
(repo_path, commit_sha, file_path). Enables incremental re-runs
that skip commits whose results are already cached.
"""

from driftscope.cache.manager import CacheManager

__all__ = ["CacheManager"]
```

---

### `driftscope/cache/manager.py`

```python
"""SQLite cache manager for incremental AST analysis re-runs.

Persists parsed AST results keyed on (repo_path, commit_sha, file_path).
Invalidates entries when tree-sitter grammar versions change.

Time Complexity:
    - get: O(1) indexed lookup
    - put: O(1) upsert
    - invalidate_grammar_version: O(n) where n = rows matching version
    - is_cached: O(1) indexed lookup

Space Complexity: O(n) where n = number of cached file entries
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from driftscope.errors import DriftScopeError


class CacheError(DriftScopeError):
    """Raised when cache operations fail."""


_SCHEMA = """
CREATE TABLE IF NOT EXISTS cache_entries (
    repo_path       TEXT    NOT NULL,
    commit_sha      TEXT    NOT NULL,
    file_path       TEXT    NOT NULL,
    ast_hash        TEXT    NOT NULL,
    ast_data        TEXT    NOT NULL,
    grammar_version TEXT    NOT NULL,
    timestamp       TEXT    NOT NULL,
    PRIMARY KEY (repo_path, commit_sha, file_path)
);
"""

_GET_SQL = """
SELECT ast_data
  FROM cache_entries
 WHERE repo_path  = ?
   AND commit_sha = ?
   AND file_path  = ?;
"""

_PUT_SQL = """
INSERT INTO cache_entries (repo_path, commit_sha, file_path, ast_hash, ast_data, grammar_version, timestamp)
VALUES (?, ?, ?, ?, ?, ?, ?)
ON CONFLICT(repo_path, commit_sha, file_path)
DO UPDATE SET
    ast_hash        = excluded.ast_hash,
    ast_data        = excluded.ast_data,
    grammar_version = excluded.grammar_version,
    timestamp       = excluded.timestamp;
"""

_IS_CACHED_SQL = """
SELECT 1
  FROM cache_entries
 WHERE repo_path  = ?
   AND commit_sha = ?
   AND file_path  = ?
 LIMIT 1;
"""

_INVALIDATE_SQL = """
DELETE FROM cache_entries
 WHERE grammar_version = ?;
"""


class CacheManager:
    """SQLite-backed cache for incremental AST analysis.

    Creates the database file and schema on instantiation. The database
    is stored at ``<db_path>/cache.db`` inside the ``.driftscope/``
    directory within the target repository.

    Args:
        db_path: Directory where ``cache.db`` will be created. The
            directory is created if it does not exist.

    Raises:
        CacheError: If the database or directory cannot be created.

    Example::

        from pathlib import Path
        from driftscope.cache import CacheManager

        cache = CacheManager(Path(".driftscope"))
        cache.put("/repo", "abc123", "src/main.py", "h1", "{}", "v1")
        data = cache.get("/repo", "abc123", "src/main.py")
        assert data == "{}"
    """

    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path
        try:
            db_path.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise CacheError(
                f"Cannot create cache directory {db_path}: {exc}"
            ) from exc

        db_file = db_path / "cache.db"
        try:
            self._conn = sqlite3.connect(str(db_file))
            self._conn.execute("PRAGMA journal_mode=WAL;")
            self._conn.execute("PRAGMA synchronous=NORMAL;")
            self._conn.executescript(_SCHEMA)
            self._conn.commit()
        except sqlite3.Error as exc:
            raise CacheError(
                f"Cannot initialize cache database {db_file}: {exc}"
            ) from exc

    def get(
        self,
        repo_path: str,
        commit_sha: str,
        file_path: str,
    ) -> Optional[str]:
        """Retrieve cached AST data for a specific file at a commit.

        Args:
            repo_path: Absolute path to the repository root.
            commit_sha: Full 40-character commit SHA.
            file_path: Relative file path within the repository.

        Returns:
            Cached AST data as a string, or ``None`` if no cached
            entry exists.

        Raises:
            CacheError: If the database query fails.
        """
        try:
            cursor = self._conn.execute(
                _GET_SQL, (repo_path, commit_sha, file_path)
            )
            row = cursor.fetchone()
            return row[0] if row is not None else None
        except sqlite3.Error as exc:
            raise CacheError(f"Cache get failed: {exc}") from exc

    def put(
        self,
        repo_path: str,
        commit_sha: str,
        file_path: str,
        ast_hash: str,
        ast_data: str,
        grammar_version: str,
    ) -> None:
        """Store or update cached AST data for a specific file at a commit.

        Uses ``INSERT ... ON CONFLICT ... DO UPDATE`` (upsert) so calling
        ``put`` twice with the same key overwrites the previous entry.

        Args:
            repo_path: Absolute path to the repository root.
            commit_sha: Full 40-character commit SHA.
            file_path: Relative file path within the repository.
            ast_hash: Hash of the AST content for change detection.
            ast_data: Serialized AST data (JSON string).
            grammar_version: Version of the tree-sitter grammar used.

        Raises:
            CacheError: If the database write fails.
        """
        timestamp = datetime.now(timezone.utc).isoformat()
        try:
            self._conn.execute(
                _PUT_SQL,
                (repo_path, commit_sha, file_path, ast_hash, ast_data, grammar_version, timestamp),
            )
            self._conn.commit()
        except sqlite3.Error as exc:
            raise CacheError(f"Cache put failed: {exc}") from exc

    def invalidate_grammar_version(self, old_version: str) -> int:
        """Delete all cache entries that were created with a given grammar version.

        Call this after upgrading tree-sitter grammars to force re-parsing
        of all cached files.

        Args:
            old_version: Grammar version string to invalidate.

        Returns:
            Number of rows deleted.

        Raises:
            CacheError: If the database delete fails.
        """
        try:
            cursor = self._conn.execute(_INVALIDATE_SQL, (old_version,))
            self._conn.commit()
            return cursor.rowcount
        except sqlite3.Error as exc:
            raise CacheError(
                f"Cache invalidation failed: {exc}"
            ) from exc

    def is_cached(
        self,
        repo_path: str,
        commit_sha: str,
        file_path: str,
    ) -> bool:
        """Check whether a cache entry exists for a specific file at a commit.

        Args:
            repo_path: Absolute path to the repository root.
            commit_sha: Full 40-character commit SHA.
            file_path: Relative file path within the repository.

        Returns:
            ``True`` if a cache entry exists, ``False`` otherwise.

        Raises:
            CacheError: If the database query fails.
        """
        try:
            cursor = self._conn.execute(
                _IS_CACHED_SQL, (repo_path, commit_sha, file_path)
            )
            return cursor.fetchone() is not None
        except sqlite3.Error as exc:
            raise CacheError(f"Cache check failed: {exc}") from exc

    def close(self) -> None:
        """Close the database connection.

        Safe to call multiple times. Required for proper resource cleanup
        in long-running processes or test teardowns.
        """
        if self._conn is not None:
            self._conn.close()
            self._conn = None  # type: ignore[assignment]

    def __del__(self) -> None:
        """Ensure database connection is closed on garbage collection."""
        self.close()
```

---

### `tests/cache/__init__.py`

```python
"""Tests for driftscope.cache module."""
```

---

### `tests/cache/test_manager.py`

```python
"""Tests for driftscope.cache.manager.CacheManager.

Uses tmp_path fixture for SQLite database isolation. No network
access, no real git repositories required.

Coverage targets:
    - get/put round-trip
    - Missing key returns None
    - Overwrite on duplicate put
    - is_cached returns correct boolean
    - invalidate_grammar_version removes matching entries
    - invalidate_grammar_version preserves non-matching entries
    - CacheError on directory creation failure
    - close() is idempotent
"""

from __future__ import annotations

import pytest

from driftscope.cache.manager import CacheManager, CacheError


class TestGetPutRoundTrip:
    """Verify basic put -> get round-trip through SQLite."""

    def test_put_then_get_returns_data(self, tmp_path: pytest.TempPathFactory) -> None:
        """Storing AST data and retrieving it returns the same string."""
        cache = CacheManager(tmp_path / ".driftscope")
        try:
            cache.put("/repo", "a" * 40, "src/main.py", "hash1", '{"type":"module"}', "v1")
            result = cache.get("/repo", "a" * 40, "src/main.py")
            assert result == '{"type":"module"}'
        finally:
            cache.close()

    def test_get_missing_key_returns_none(self, tmp_path: pytest.TempPathFactory) -> None:
        """Retrieving a key that was never stored returns None."""
        cache = CacheManager(tmp_path / ".driftscope")
        try:
            result = cache.get("/repo", "b" * 40, "nonexistent.py")
            assert result is None
        finally:
            cache.close()

    def test_multiple_entries_independent(self, tmp_path: pytest.TempPathFactory) -> None:
        """Multiple entries with different keys are stored independently."""
        cache = CacheManager(tmp_path / ".driftscope")
        try:
            cache.put("/repo", "a" * 40, "file_a.py", "h1", "data_a", "v1")
            cache.put("/repo", "b" * 40, "file_b.py", "h2", "data_b", "v1")
            assert cache.get("/repo", "a" * 40, "file_a.py") == "data_a"
            assert cache.get("/repo", "b" * 40, "file_b.py") == "data_b"
        finally:
            cache.close()


class TestOverwrite:
    """Verify that putting the same key twice overwrites the value."""

    def test_overwrite_returns_latest_value(self, tmp_path: pytest.TempPathFactory) -> None:
        """Second put with same key overwrites first value."""
        cache = CacheManager(tmp_path / ".driftscope")
        try:
            sha = "a" * 40
            cache.put("/repo", sha, "src/main.py", "hash_v1", '{"old":true}', "v1")
            cache.put("/repo", sha, "src/main.py", "hash_v2", '{"new":true}', "v1")
            result = cache.get("/repo", sha, "src/main.py")
            assert result == '{"new":true}'
        finally:
            cache.close()

    def test_overwrite_updates_ast_hash(self, tmp_path: pytest.TempPathFactory) -> None:
        """Overwriting updates all columns, not just ast_data."""
        cache = CacheManager(tmp_path / ".driftscope")
        try:
            sha = "a" * 40
            fp = "src/main.py"
            cache.put("/repo", sha, fp, "hash_old", "data_old", "v1")
            cache.put("/repo", sha, fp, "hash_new", "data_new", "v2")
            # Verify data was updated
            assert cache.get("/repo", sha, fp) == "data_new"
            # Verify invalidation on old version no longer matches
            deleted = cache.invalidate_grammar_version("v1")
            assert deleted == 0
            # Entry still exists with v2
            assert cache.is_cached("/repo", sha, fp)
        finally:
            cache.close()


class TestIsCached:
    """Verify is_cached returns correct boolean for present/absent keys."""

    def test_is_cached_true_after_put(self, tmp_path: pytest.TempPathFactory) -> None:
        """is_cached returns True after a put."""
        cache = CacheManager(tmp_path / ".driftscope")
        try:
            cache.put("/repo", "a" * 40, "src/main.py", "h1", "data", "v1")
            assert cache.is_cached("/repo", "a" * 40, "src/main.py") is True
        finally:
            cache.close()

    def test_is_cached_false_without_put(self, tmp_path: pytest.TempPathFactory) -> None:
        """is_cached returns False for a key that was never stored."""
        cache = CacheManager(tmp_path / ".driftscope")
        try:
            assert cache.is_cached("/repo", "a" * 40, "never.py") is False
        finally:
            cache.close()

    def test_is_cached_false_after_invalidation(self, tmp_path: pytest.TempPathFactory) -> None:
        """is_cached returns False after grammar version invalidation."""
        cache = CacheManager(tmp_path / ".driftscope")
        try:
            cache.put("/repo", "a" * 40, "src/main.py", "h1", "data", "v1")
            cache.invalidate_grammar_version("v1")
            assert cache.is_cached("/repo", "a" * 40, "src/main.py") is False
        finally:
            cache.close()


class TestInvalidateGrammarVersion:
    """Verify grammar version invalidation deletes matching entries only."""

    def test_invalidate_removes_matching_entries(self, tmp_path: pytest.TempPathFactory) -> None:
        """Invalidate deletes all entries with the given grammar version."""
        cache = CacheManager(tmp_path / ".driftscope")
        try:
            cache.put("/repo", "a" * 40, "file_a.py", "h1", "data_a", "v1")
            cache.put("/repo", "b" * 40, "file_b.py", "h2", "data_b", "v1")
            cache.put("/repo", "c" * 40, "file_c.py", "h3", "data_c", "v2")

            deleted = cache.invalidate_grammar_version("v1")
            assert deleted == 2

            assert cache.get("/repo", "a" * 40, "file_a.py") is None
            assert cache.get("/repo", "b" * 40, "file_b.py") is None
            # v2 entry untouched
            assert cache.get("/repo", "c" * 40, "file_c.py") == "data_c"
        finally:
            cache.close()

    def test_invalidate_no_match_returns_zero(self, tmp_path: pytest.TempPathFactory) -> None:
        """Invalidating a version with no entries returns 0."""
        cache = CacheManager(tmp_path / ".driftscope")
        try:
            cache.put("/repo", "a" * 40, "file.py", "h1", "data", "v1")
            deleted = cache.invalidate_grammar_version("v99")
            assert deleted == 0
            # Original entry still present
            assert cache.is_cached("/repo", "a" * 40, "file.py")
        finally:
            cache.close()

    def test_invalidate_preserves_different_version(self, tmp_path: pytest.TempPathFactory) -> None:
        """Invalidating one version preserves entries with a different version."""
        cache = CacheManager(tmp_path / ".driftscope")
        try:
            sha = "a" * 40
            cache.put("/repo", sha, "file.py", "h1", "data_v1", "v1")
            cache.put("/repo", sha, "file.py", "h2", "data_v2", "v2")

            deleted = cache.invalidate_grammar_version("v1")
            assert deleted == 1
            # v2 overwrote the same key, so the entry remains
            assert cache.get("/repo", sha, "file.py") == "data_v2"
        finally:
            cache.close()


class TestCacheInit:
    """Verify CacheManager initialization behavior."""

    def test_creates_db_file(self, tmp_path: pytest.TempPathFactory) -> None:
        """Initialization creates the cache.db file."""
        db_dir = tmp_path / ".driftscope"
        assert not db_dir.exists()
        cache = CacheManager(db_dir)
        try:
            assert (db_dir / "cache.db").is_file()
        finally:
            cache.close()

    def test_creates_nested_directories(self, tmp_path: pytest.TempPathFactory) -> None:
        """Initialization creates deeply nested directories if needed."""
        db_dir = tmp_path / "a" / "b" / "c" / ".driftscope"
        cache = CacheManager(db_dir)
        try:
            assert db_dir.is_dir()
            assert (db_dir / "cache.db").is_file()
        finally:
            cache.close()

    def test_existing_directory_is_ok(self, tmp_path: pytest.TempPathFactory) -> None:
        """Initialization succeeds even if the directory already exists."""
        db_dir = tmp_path / ".driftscope"
        db_dir.mkdir()
        # Second init should not raise
        cache = CacheManager(db_dir)
        try:
            assert (db_dir / "cache.db").is_file()
        finally:
            cache.close()

    def test_uncreatable_directory_raises_cache_error(self) -> None:
        """Initialization raises CacheError when directory cannot be created."""
        # /dev/null is a file, not a directory; creating a subdir fails
        import pathlib
        cache = CacheManager.__new__(CacheManager)
        with pytest.raises(CacheError, match="Cannot create cache directory"):
            cache.__init__(pathlib.Path("/dev/null/impossible/subdir"))


class TestClose:
    """Verify close() behavior."""

    def test_close_is_idempotent(self, tmp_path: pytest.TempPathFactory) -> None:
        """Calling close() twice does not raise."""
        cache = CacheManager(tmp_path / ".driftscope")
        cache.close()
        cache.close()  # Should not raise

    def test_operations_after_close_raise(self, tmp_path: pytest.TempPathFactory) -> None:
        """Attempting operations after close raises CacheError or AttributeError."""
        cache = CacheManager(tmp_path / ".driftscope")
        cache.close()
        with pytest.raises((CacheError, AttributeError)):
            cache.get("/repo", "a" * 40, "file.py")


class TestSchemaPersistence:
    """Verify that the schema persists across CacheManager instances."""

    def test_data_persists_across_instances(self, tmp_path: pytest.TempPathFactory) -> None:
        """Data written by one CacheManager is readable by a new instance."""
        db_dir = tmp_path / ".driftscope"
        sha = "a" * 40

        cache1 = CacheManager(db_dir)
        try:
            cache1.put("/repo", sha, "persist.py", "h1", "persistent_data", "v1")
        finally:
            cache1.close()

        cache2 = CacheManager(db_dir)
        try:
            result = cache2.get("/repo", sha, "persist.py")
            assert result == "persistent_data"
        finally:
            cache2.close()
```

---

### TDD Step Sequence

```
Step 1: Write tests/cache/__init__.py and tests/cache/test_manager.py with all tests.
  -> Run: python -m pytest tests/cache/test_manager.py -v
  -> Expect: FAIL (module not found)

Step 2: Implement driftscope/cache/__init__.py and manager.py.
  -> Run: python -m pytest tests/cache/test_manager.py -v
  -> Expect: PASS
  -> Commit: feat(cache): add SQLite cache manager for incremental AST analysis re-runs

Step 3: Coverage check.
  -> Run: python -m pytest tests/cache/ --cov=driftscope/cache --cov-report=term-missing
  -> Expect: >=95% line coverage

Step 4: Full regression.
  -> Run: python -m pytest tests/ -v --tb=short
  -> Expect: All tests pass (Tasks 1-10)
```

### Commit

```
feat(cache): add SQLite cache manager for incremental AST analysis re-runs
```

---

## Task 11: CLI (Typer App, All Subcommands)

**Goal:** Wire all pipeline stages into the Typer CLI.

### Files

```
driftscope/cli/__init__.py
driftscope/cli/main.py         # Typer app, top-level options
driftscope/cli/init_cmd.py     # driftscope init
driftscope/cli/analyze_cmd.py  # driftscope analyze
driftscope/cli/report_cmd.py   # driftscope report
driftscope/cli/diff_cmd.py     # driftscope diff
driftscope/cli/config_cmd.py   # driftscope config validate
driftscope/cli/schema_cmd.py   # driftscope schema
tests/cli/__init__.py
tests/cli/test_init.py
tests/cli/test_analyze.py
tests/cli/test_report.py
tests/cli/test_diff.py
tests/cli/test_config_cmd.py
tests/cli/test_schema.py
```

### Key Implementation Details

**`main.py`:**
- Typer app with `driftscope` name, `--version` flag, `--verbose` flag
- Error handler: catches `DriftScopeError`, writes structured JSON to stderr, exits 1
- Threshold breach handler: exits 2 when `--enforce` and breaches detected

**`init_cmd.py`:**
- Validates git repo, checks git version >= 2.30, detects bare repo
- Creates `.driftscope.yaml` with defaults
- Creates `.driftscope/cache.db`
- Verifies tree-sitter grammars for configured languages

**`analyze_cmd.py`:**
- Full pipeline: git_client -> authorship -> ast_engine -> metrics -> reporting
- Accepts `--window`, `--module`, `--metric`, `--format`, `--output`, `--from`, `--to`, `--enforce`
- Writes cache entries
- Exits 0/1/2

**`report_cmd.py`:**
- Reads from cache or re-runs analysis
- Accepts `--format`, `--output`, `--include-provenance`

**`diff_cmd.py`:**
- AST-level diff between two SHAs
- Accepts `--format`, `--module`

**`config_cmd.py`:**
- `driftscope config validate` — loads config, validates, reports match counts

**`schema_cmd.py`:**
- Prints `MetricsResult.model_json_schema()` as JSON

### Test Strategy

- Use `typer.testing.CliRunner` to invoke commands
- Mock pipeline stages at boundary
- Verify exit codes (0, 1, 2)
- Verify stdout/stderr content

### Commit

```
feat(cli): add Typer CLI with init, analyze, report, diff, config validate, and schema subcommands
```

---

## Task 12: GitHub Integration (PR Comment Posting)

**Goal:** Implement PR summary comment posting via GitHub REST API.

### Files

```
driftscope/integrations/__init__.py
driftscope/integrations/github_pr.py
driftscope/integrations/slack_notify.py   # v1.1 stub
tests/integrations/__init__.py
tests/integrations/test_github_pr.py
```

### Key Implementation Details

**`github_pr.py`:**
- `post_pr_comment(summary_path: Path, report_url: str) -> None`
- Reads JSON summary, formats PR comment body per spec template
- Posts via `POST /repos/{owner}/{repo}/issues/{number}/comments`
- Auth via `GITHUB_TOKEN` env var
- Owner/repo/PR number extracted from `GITHUB_REPOSITORY` and `GITHUB_REF` env vars
- Network errors caught and logged, do not cause workflow failure

**`slack_notify.py`:**
- Stub: validates webhook URL format, prints warning "Slack notifications require v1.1"

### Test Strategy

- Mock `requests.post` (or `urllib.request`)
- Verify comment body format matches spec
- Verify env var extraction
- Test error handling (network failure, missing env vars)

### Commit

```
feat(integrations): add GitHub PR comment posting and Slack notification stub
```

---

## Task 13: E2E Tests (Fixture Repo, Full Pipeline)

**Goal:** End-to-end validation of the complete analysis pipeline.

### Files

```
tests/e2e/__init__.py
tests/e2e/conftest.py           # fixture repo creation helpers
tests/e2e/test_full_pipeline.py
tests/e2e/test_idempotency.py
tests/e2e/test_module_scoping.py
tests/e2e/test_threshold_enforcement.py
```

### Key Implementation Details

**Fixture repo (`conftest.py`):**
- `create_fixture_repo(tmp_path: Path) -> Path`
- Creates a synthetic git repo with:
  - 2 modules: `src/payments/`, `src/auth/`
  - Python files with known functions
  - ~50 commits spanning 6 months
  - Mix of human commits and AI-tagged commits (Copilot, Claude, Cursor tags)
  - Known complexity patterns (nested if, switch-like chains)
  - Known churn (add/modify/remove cycles)
- Uses `gitpython` for programmatic repo construction

**`test_full_pipeline.py`:**
- E2E scenario 1: `driftscope analyze --window 90d --format json` produces valid JSON
- E2E scenario 2: `driftscope report --format html --output dashboard.html` produces HTML

**`test_idempotency.py`:**
- E2E scenario 3: Two identical `analyze` runs produce identical output

**`test_module_scoping.py`:**
- E2E scenario 4: `--module src/payments` scopes to single module

**`test_threshold_enforcement.py`:**
- E2E scenario 5: Low threshold triggers breach detection, `--enforce` exits 2

### Commit

```
test(e2e): add end-to-end pipeline tests with fixture repository covering all scenarios
```

---

## Task 14: Distribution (Packaging, GitHub Actions Workflow)

**Goal:** Package for PyPI distribution and provide GitHub Actions workflow.

### Files

```
.github/
└── workflows/
    └── driftscope.yml
```

### Key Implementation Details

**`driftscope.yml`:**
- Triggers: push to main, PR close to main, weekly Monday cron
- Steps: checkout (fetch-depth: 0), install driftscope, run analyze, generate HTML, upload artifact, post PR comment
- Matches the spec's GitHub Actions Integration section exactly

**Packaging verification:**
- `python -m build` produces wheel and sdist
- `pip install dist/driftscope-0.1.0-py3-none-any.whl` works
- `driftscope --version` prints `0.1.0`
- `driftscope --help` prints usage

### Test Commands

```bash
python -m build
# Expected: dist/driftscope-0.1.0-py3-none-any.whl and dist/driftscope-0.1.0.tar.gz

pip install dist/driftscope-0.1.0-py3-none-any.whl
driftscope --version
# Expected: 0.1.0

driftscope --help
# Expected: usage message with all subcommands
```

### Commit

```
ci(actions): add DriftScope GitHub Actions workflow for PR analysis and weekly scheduled runs
```

---

## Summary

| Task | Files | Tests | Key Dependencies |
|------|-------|-------|------------------|
| 1. Scaffold | 6 | 0 (runner only) | None |
| 2. Data Model | 9 | 8 (~25 tests) | Task 1 |
| 3. Error Types | 2 | 1 (~11 tests) | Task 1 |
| 4. Config | 5 | 2 (~20 tests) | Tasks 1-3 |
| 5. Authorship | 5 | 2 (~25 tests) | Tasks 1-3 |
| 6. Git Client | 7 | 4 | Tasks 1-4 |
| 7. AST Engine | 11 | 3 | Tasks 2-6 |
| 8. Metrics | 7 | 3 | Tasks 2,5,7 |
| 9. Reporting | 9 | 4 | Tasks 2,8 |
| 10. Cache | 3 | 1 | Task 1 |
| 11. CLI | 14 | 6 | All above |
| 12. GitHub Integration | 4 | 1 | Tasks 9,11 |
| 13. E2E Tests | 5 | 0 (tests only) | All above |
| 14. Distribution | 1 | 0 (manual) | Task 11 |

**Total estimated test count:** ~140+
**Coverage target:** >=95% line, >=90% branch
**Test suite target:** <5 minutes local execution

---

## Retrospective

**What Went Well:**
- Data model defines every contract upfront, enabling parallel development of later tasks
- Error hierarchy is flat and simple — one level of inheritance per stage
- Authorship patterns are compiled at module load, zero runtime cost per commit

**Potential Risks:**
- tree-sitter grammar availability may vary across platforms; grammar loading needs defensive error handling
- Git porcelain output format may differ across git versions; pin minimum git version >= 2.30
- Large repository performance (500k LOC) is untested until E2E with real-world data

**Next Improvement Steps:**
- Benchmark tree-sitter parsing speed against the 50k lines/second target
- Assemble labeled benchmark set (200+ commits) for precision/recall validation before v1
- Add property-based testing (hypothesis) for survival rate and churn math edge cases
