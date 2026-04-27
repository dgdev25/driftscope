# DriftScope: System Design Specification

**Date:** 2026-04-27
**Status:** Draft
**PRD:** `driftscope-longitudinal-ai-code-contribution-quality-monitor-prd.md`

---

## Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Authorship attribution | Tag-only (explicit co-authorship tags) | Highest precision, no false positives, defensible to stakeholders |
| Complexity metrics | Cyclomatic + cognitive | Cognitive captures nesting/conditionals cyclomatic misses; Halstead adds too much v1 cost |
| GitHub Actions enforcement | Opt-in (default: report only) | Safer default for a measurement tool; avoids blocking merges by accident |
| AST survival definition | Exact node survival | Strictest signal — code removed or rewritten shows as non-surviving |
| Disk persistence | Always persist intermediate data | Enables incremental re-runs via SQLite cache; simpler architecture |
| Language | Python | Natural CLI fit, rich git/AST ecosystem, PyPI distribution |
| Architecture | Monolithic pipeline (Approach A) | Data flow is inherently sequential; 5 languages don't justify plugin system |
| Scope | Full v1 feature set | All features from PRD: 5 languages, GitHub Actions, dashboards, all subcommands |
| Bare repository support | Supported | File content extracted via `git show` instead of filesystem reads |

### Precision/Recall Acknowledgment (PRD Open Question 1)

Tag-only attribution accepts a systematic undercount of AI contribution: any AI-assisted commit without an explicit co-authorship tag is classified as human. This means:
- **Precision** is near-100% for the AI class (every tagged commit is genuinely AI-assisted)
- **Recall** is limited by tag coverage, which varies by tool and developer behavior
- The PRD targets of ≥90% precision / ≥85% recall apply to tag-only classification validated against a labeled benchmark set. Before v1 ships, a labeled benchmark must be assembled (minimum 200 commits across Copilot, Claude Code, Cursor, and manual commits) to confirm these targets are met. If recall falls below 85% due to low tag coverage, the tool should document the measured recall rate transparently in every report rather than silently claiming the target.

### Privacy Tradeoff (PRD Open Question 4)

Choosing "always persist" means DriftScope writes git blame output and commit message content to `.driftscope/cache.db` on disk. Organizations with policies prohibiting this can restrict DriftScope to CI-only execution where the workspace is ephemeral. A future `--no-persist` mode would require an in-memory pipeline variant and is documented as a v1.1 candidate.

---

## Module Definition

A **module** is a top-level directory under the repository root. Given a repo with:

```
src/payments/
src/auth/
src/api/
lib/
scripts/
```

The modules are `src/payments`, `src/auth`, `src/api`, `lib`, `scripts`. The `--module` flag accepts a path prefix: `--module src/payments` scopes analysis to that directory and all subdirectories.

Modules are identified by scanning for directories containing source files matching the configured languages. Directories with fewer than `min_lines_per_module` total source lines are excluded from reports.

This definition is consistent across all metrics, reports, and CLI flags. Monorepo per-package scoping (v1.1) will layer on top of this with a `modules.map` config key.

---

## Package Structure

```
driftscope/
├── __init__.py
├── __main__.py                  # python -m driftscope entry
├── cli/
│   ├── __init__.py
│   ├── main.py                  # Typer app, subcommand routing
│   ├── init_cmd.py              # driftscope init
│   ├── analyze_cmd.py           # driftscope analyze
│   ├── report_cmd.py            # driftscope report
│   ├── diff_cmd.py              # driftscope diff
│   └── config_cmd.py            # driftscope config validate
├── git_client/
│   ├── __init__.py
│   ├── blame.py                 # git blame invocation + parsing
│   ├── log.py                   # git log parsing, commit metadata
│   └── diff_parser.py           # unified diff parsing for line mapping
├── authorship/
│   ├── __init__.py
│   ├── classifier.py            # human/AI classification engine
│   └── patterns.py              # co-authorship tag regex patterns
├── ast_engine/
│   ├── __init__.py
│   ├── parser.py                # tree-sitter parsing facade
│   ├── differ.py                # AST-level diff computation
│   ├── survival.py              # exact node survival tracking
│   └── grammars/                # versioned grammar definitions
│       ├── python.py
│       ├── typescript.py
│       ├── go.py
│       ├── java.py
│       └── ruby.py
├── metrics/
│   ├── __init__.py
│   ├── survival.py              # line survival rate computation
│   ├── complexity.py            # cyclomatic + cognitive complexity
│   └── churn.py                 # module-level churn attribution
├── reporting/
│   ├── __init__.py
│   ├── markdown.py              # GFM output
│   ├── html.py                  # self-contained HTML dashboard
│   ├── json_report.py           # versioned JSON schema output
│   ├── csv_export.py            # tabular CSV export
│   └── templates/               # HTML/CSS dashboard templates
├── integrations/
│   ├── __init__.py
│   ├── github_pr.py             # PR comment posting via GitHub REST API
│   └── slack_notify.py          # Slack webhook notifications (v1.1 stub)
├── config/
│   ├── __init__.py
│   ├── loader.py                # .driftscope.yaml loading
│   └── schema.py                # Pydantic config model
└── cache/
    ├── __init__.py
    └── manager.py               # incremental analysis cache (SQLite)
```

**Key technology choices:**
- **Typer** for CLI — type-annotated, auto-generated help, native subcommand support
- **Pydantic v2** for config validation and JSON report schema
- **SQLite** for analysis cache — enables incremental re-runs without re-parsing unchanged history
- **tree-sitter** via `tree-sitter` Python bindings — one parser per grammar, versioned per release

---

## Data Model

The typed data structures that flow between pipeline stages.

### Commit

```python
class Commit(BaseModel):
    sha: str                           # full 40-char SHA
    short_sha: str                     # first 7 chars
    timestamp: datetime                # commit author timestamp (UTC)
    author_name: str
    author_email: str
    committer_name: str                # distinct from author for AI-tagged commits
    committer_email: str
    message_subject: str
    message_body: str                  # full body including trailers
    parent_shas: list[str]             # 1 for normal, 2+ for merge commits
```

### BlameLine

```python
class BlameLine(BaseModel):
    line_number: int                   # 1-based line in the file at HEAD
    commit_sha: str                    # originating commit SHA
    author_name: str
    author_email: str
    content: str                       # the line content (stripped)
```

### CommitHistory

```python
class CommitHistory(BaseModel):
    repo_path: Path
    commits: list[Commit]              # ordered oldest → newest within range
    blame: dict[Path, list[BlameLine]] # file path → blame results at HEAD
    range_start: datetime
    range_end: datetime
```

### AttributedCommit

```python
class AttributedCommit(Commit):
    authorship_class: Literal["human", "ai"]
    matched_pattern: str | None        # the regex pattern that matched, if AI
    matched_text: str | None           # the actual text that matched
```

### AttributedHistory

```python
class AttributedHistory(BaseModel):
    repo_path: Path
    commits: list[AttributedCommit]
    blame: dict[Path, list[BlameLine]]
    range_start: datetime
    range_end: datetime
    ai_commit_count: int
    human_commit_count: int
```

### ASTNodeChange

```python
class ASTNodeChange(BaseModel):
    node_type: str                     # e.g., "function_definition", "if_statement"
    start_line: int
    end_line: int
    change_type: Literal["added", "removed", "modified"]
    text_hash: str                     # hash of node text for exact survival matching
```

### ASTFileDiff

```python
class ASTFileDiff(BaseModel):
    file_path: Path
    commit_sha: str
    before_hash: str | None            # hash of AST before commit (None for new files)
    after_hash: str | None             # hash of AST after commit (None for deleted files)
    changes: list[ASTNodeChange]
    authorship_class: Literal["human", "ai"]
```

### ASTDiffSet

```python
class ASTDiffSet(BaseModel):
    diffs: list[ASTFileDiff]
    skipped_files: list[dict[str, str]]  # {"path": "...", "reason": "unsupported_extension"}
```

### ModuleMetrics

```python
class ModuleMetrics(BaseModel):
    module_path: str
    total_lines: int
    ai_lines: int
    human_lines: int

    survival: dict[str, SurvivalMetrics]    # keyed by window ("30d", "90d", etc.)
    complexity: ComplexityMetrics
    churn: ChurnMetrics
```

### SurvivalMetrics

```python
class SurvivalMetrics(BaseModel):
    window: str                          # "30d", "90d", "180d", "365d"
    ai_lines_introduced: int
    ai_lines_surviving: int
    ai_survival_rate: float              # 0.0-1.0
    human_lines_introduced: int
    human_lines_surviving: int
    human_survival_rate: float
```

### ComplexityMetrics

```python
class ComplexityMetrics(BaseModel):
    cyclomatic_delta_ai: float           # mean delta per AI commit
    cyclomatic_delta_human: float        # mean delta per human commit
    cognitive_delta_ai: float
    cognitive_delta_human: float
    weekly_series: list[WeeklyComplexity]  # for time-series output
```

### WeeklyComplexity

```python
class WeeklyComplexity(BaseModel):
    week_start: date
    ai_cyclomatic_mean: float
    human_cyclomatic_mean: float
    ai_cognitive_mean: float
    human_cognitive_mean: float
    ai_commit_count: int
    human_commit_count: int
```

### ChurnMetrics

```python
class ChurnMetrics(BaseModel):
    total_churn_lines: int               # lines added + removed in rolling 365d
    ai_churn_lines: int                  # churn traceable to AI-introduced code
    ai_churn_attribution_pct: float      # 0.0-100.0
```

### MetricsResult

```python
class MetricsResult(BaseModel):
    repo_path: Path
    commit_range: tuple[str, str]        # (start SHA, end SHA)
    range_start: datetime
    range_end: datetime
    schema_version: str                  # "1.0.0"
    modules: list[ModuleMetrics]
    skipped_files: list[dict[str, str]]
    data_incomplete: bool                # true if window shorter than commit span
    threshold_breaches: list[ThresholdBreach]
```

### ThresholdBreach

```python
class ThresholdBreach(BaseModel):
    metric: str                          # "ai_churn_attribution_pct" or "ai_survival_rate_pct"
    module_path: str
    value: float
    threshold: float
    direction: Literal["above", "below"]
```

### ProvenanceEntry (for `--include-provenance`)

```python
class ProvenanceEntry(BaseModel):
    file_path: str
    line_start: int
    line_end: int
    authorship_class: Literal["human", "ai"]
    originating_commit_sha: str
    commit_timestamp: datetime
    co_authorship_tag: str | None        # the matched tag text, if AI
```

---

## Data Flow & Pipeline

The analysis pipeline runs as a strict sequence. Each stage produces a typed data structure consumed by the next.

```
┌─────────────┐    ┌──────────────┐    ┌─────────────┐    ┌────────────┐    ┌───────────┐
│  git_client  │───▶│  authorship  │───▶│  ast_engine  │───▶│  metrics   │───▶│ reporting  │
│              │    │              │    │              │    │            │    │           │
│ blame + log  │    │ classify     │    │ parse + diff │    │ survival   │    │ md/html/  │
│ commit data  │    │ human/AI     │    │ node tracking│    │ complexity │    │ json/csv  │
└─────────────┘    └──────────────┘    └─────────────┘    └────────────┘    └───────────┘
       ▲                                       │
       │                                       ▼
       │                                ┌─────────────┐
       └────────────────────────────────│    cache     │
                  cache hit/miss        │  (SQLite)   │
                                        └─────────────┘
```

### Stage 1 — git_client

**Produces:** `CommitHistory`

- Ordered list of `Commit` objects via `git log`
- Per-file `BlameLine` results via `git blame` at HEAD
- **Inputs:** repo path, commit range (SHA or date window), file filter
- **Bare repos:** File content for tree-sitter extracted via `git show SHA:PATH` rather than filesystem reads. `driftscope init` detects bare repos and configures this mode automatically.

### Stage 2 — authorship

**Consumes:** `CommitHistory`
**Produces:** `AttributedHistory`

- Each `Commit` upgraded to `AttributedCommit` with `authorship_class: Literal["human", "ai"]`
- Tag matching against commit message body using compiled regex patterns
- Built-in patterns:
  - GitHub Copilot: `Co-Authored-By: GitHub Copilot`
  - Claude Code: `Co-Authored-By: Claude`
  - Cursor AI
  - Devin
  - Generic: `AI-Generated:` trailer
- Custom patterns from `.driftscope.yaml` applied in addition unless `builtin_patterns: false`
- Any match = AI, no match = human (deterministic, no heuristics)

### Stage 3 — ast_engine

**Consumes:** `AttributedHistory`
**Produces:** `ASTDiffSet`

- For each commit, parse before/after file states with tree-sitter
- Compute AST-level diffs: added nodes, removed nodes, modified nodes
- Track exact node survival: a node introduced by commit X survives if it exists unchanged at window end (matched by `text_hash`)
- Output: `ASTFileDiff` per commit per file

### Stage 4 — metrics

**Consumes:** `AttributedHistory` + `ASTDiffSet`
**Produces:** `MetricsResult`

- **survival.py** — line survival rate at 30/90/180/365-day windows, segmented by author type, per module
- **complexity.py** — cyclomatic complexity delta + cognitive complexity delta per commit, segmented by author type, with weekly time-series breakdown
- **churn.py** — rolling 365-day churn attribution per module (percentage traceable to AI-introduced code)
- All metrics at function, file, and module granularity
- Modules with all files skipped are excluded from the report entirely

### Stage 5 — reporting

**Consumes:** `MetricsResult`
**Produces:** Output files

- Each format module receives the same `MetricsResult`
- JSON output validates against versioned Pydantic schema
- HTML is self-contained single file: inline CSS, no CDN, no JS dependencies
- `skipped_files` counter included in all report outputs
- Threshold breach status included as a top-level field in all formats

### Cache Layer

- SQLite database at `.driftscope/cache.db`
- Keyed on (repo path, commit SHA, file path)
- Stores parsed AST results and blame data
- On re-run, skips commits whose SHA results are already cached
- Invalidated when tree-sitter grammar versions change

---

## Error Handling

**Core principle:** Fail loudly, never silently. Every error produces a non-zero exit code and a structured JSON error payload to stderr.

### Error Hierarchy

```python
class DriftScopeError(Exception):
    """Base — all errors inherit from this."""

class ConfigError(DriftScopeError):
    """Invalid .driftscope.yaml: bad regex, missing required field, unknown key."""

class GitError(DriftScopeError):
    """git binary failures: not a repo, no history, authentication issue, binary not found."""

class AuthorshipError(DriftScopeError):
    """Pattern compilation failures: invalid regex in custom patterns."""

class ASTParseError(DriftScopeError):
    """tree-sitter parsing failures: unsupported language, corrupted grammar, file too large."""

class MetricError(DriftScopeError):
    """Computation failures: empty window, insufficient data, division by zero."""

class ReportError(DriftScopeError):
    """Output failures: disk full, permission denied, template rendering error."""
```

### Failure Behavior Per Stage

| Stage | Failure mode | Behavior |
|-------|-------------|----------|
| `git_client` | git binary not found | Exit with `GitError` + install instructions |
| `git_client` | Empty repo / no commits | Exit with `GitError` |
| `git_client` | Commit range yields zero results | Exit with `GitError` — invalid range |
| `authorship` | Invalid custom regex pattern | Exit with `AuthorshipError` showing bad pattern + position |
| `ast_engine` | Unsupported file extension | Skip file silently, increment `skipped_files` counter |
| `ast_engine` | tree-sitter parse timeout (>5s per file) | Skip file, log warning, increment `skipped_files` |
| `ast_engine` | Grammar not installed | Exit with `ASTParseError` |
| `ast_engine` | ALL files in a module skipped | Module excluded from report, noted in `skipped_files` summary |
| `metrics` | Module below minimum line threshold | Exclude from report (configurable, default 10 lines) |
| `metrics` | Window shorter than commit span | Compute with available data, set `data_incomplete: true` |
| `reporting` | Disk write failure | Exit with `ReportError` |
| `config` | `.driftscope.yaml` not found | Use built-in defaults |
| `config` | `config validate` with invalid config | Print each error with line number, exit 1 |

### Structured Error Output (stderr)

```json
{
  "error": {
    "type": "ASTParseError",
    "message": "tree-sitter parse timeout on src/large_file.py (5.2s > 5.0s limit)",
    "stage": "ast_engine",
    "file": "src/large_file.py",
    "suggestion": "Increase timeout with --parse-timeout or exclude with .driftscope.yaml"
  }
}
```

### GitHub Actions Error Surfacing

Analysis errors surface as workflow annotations (`::error::` syntax). Notification delivery failures (Slack webhook down) are caught and logged but do not cause workflow failure.

---

## Threshold Enforcement

Thresholds are evaluated at module level. A breach occurs when a module's metric value crosses the configured threshold.

**Enforcement model:**
- Default: report breaches in output, exit 0
- With `--enforce` flag: exit 2 on any breach (exit 2 distinguishes threshold breaches from errors which exit 1)
- `--enforce` can be set in `.driftscope.yaml` as `thresholds.enforce: true` or via CLI flag

**Threshold configuration:**

```yaml
thresholds:
  enforce: false                     # true to exit 2 on breach
  ai_churn_attribution_pct: null     # breach if module value > threshold
  ai_survival_rate_pct: null         # breach if module value < threshold
```

**Breach output (included in all report formats):**

```json
{
  "threshold_breaches": [
    {
      "metric": "ai_churn_attribution_pct",
      "module_path": "src/payments",
      "value": 62.5,
      "threshold": 50.0,
      "direction": "above"
    }
  ]
}
```

**GitHub Actions behavior:** When `--enforce` is active, the workflow step exits 2, and the `::error::` annotation includes the module, metric, value, and threshold.

---

## GitHub Actions Integration

### Workflow YAML

```yaml
name: DriftScope Analysis

on:
  push:
    branches: [main]
  pull_request:
    types: [closed]
    branches: [main]
  schedule:
    - cron: '0 6 * * 1'  # Every Monday 6:00 UTC

jobs:
  analyze:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      pull-requests: write

    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0  # Full history required for analysis

      - name: Install DriftScope
        run: pip install driftscope

      - name: Run Analysis
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          driftscope analyze \
            --window 90d \
            --format json \
            --output driftscope-report.json \
            ${{ github.event_name == 'schedule' && '--enforce' || '' }}

      - name: Generate HTML Dashboard
        if: always()
        run: driftscope report --format html --output dashboard.html

      - name: Upload Report Artifact
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: driftscope-report
          path: |
            driftscope-report.json
            dashboard.html

      - name: Post PR Comment
        if: github.event_name == 'pull_request'
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          driftscope report \
            --format json \
            --include-provenance \
            --output pr-summary.json
          python -m driftscope.integrations.github_pr \
            --summary pr-summary.json \
            --report-url "${{ github.server_url }}/${{ github.repository }}/actions/runs/${{ github.run_id }}"
```

### PR Comment Format

Posted by `integrations/github_pr.py` via GitHub REST API `POST /repos/{owner}/{repo}/issues/{number}/comments`:

```markdown
## DriftScope: AI Code Quality Summary

| Metric | This PR | Repo Average |
|--------|---------|-------------|
| AI-authored lines | 142 | — |
| Projected churn risk | Medium | Low |
| Complexity delta | +2.1 | +0.8 |

**Modules affected:** `src/payments`, `src/api`

📊 [Full Report]({report_url})
```

Required permissions: `pull-requests: write` on `GITHUB_TOKEN`.

### Slack Notification (v1.1 Stub)

The `notifications.slack_webhook` config key is accepted in v1 but produces a warning: `"Slack notifications require v1.1"`. The `integrations/slack_notify.py` module is a stub that validates the webhook URL format and exits. Full implementation deferred to v1.1 per PRD "Should Have" classification.

---

## HTML Dashboard Layout

The self-contained HTML dashboard produced by `report --format html` contains these sections:

**1. Header** — Repo name, analysis date range, commit SHA range, schema version

**2. Executive Summary Table** — One row per module:

| Module | AI Lines | Survival (90d) | Churn Attribution | Complexity Δ (AI) |
|--------|----------|----------------|-------------------|--------------------|
| src/payments | 1,204 | 67% | 42% | +3.2 |
| src/api | 892 | 81% | 28% | +1.1 |

**3. Survival Trend Table** — Per module, per window, no JS rendering:
- Static HTML table with weekly rows
- Columns: week start, AI survival rate, human survival rate
- ASCII sparklines in cells for visual trend (e.g., `▁▂▃▅▆▇`)

**4. Complexity Trend Table** — Weekly data points matching `--metric complexity-delta` output:
- Columns: week, AI cyclomatic mean, human cyclomatic mean, AI cognitive mean, human cognitive mean

**5. Churn Attribution Table** — Per module, rolling 365d:
- Columns: module, total churn lines, AI churn lines, AI attribution percentage

**6. Threshold Status** — Which modules breached thresholds, values vs. configured limits

**7. Skipped Files** — List of files skipped during analysis with reasons

**8. Metadata** — DriftScope version, grammar versions, analysis duration, `data_incomplete` flag

**Historical data:** Each weekly run overwrites the HTML file. For GitHub Pages deployment, teams can configure their workflow to commit the dashboard to a `gh-pages` branch, accumulating history via git. The HTML file itself is a snapshot — trend data within the file covers the analysis window, not all historical runs.

---

## JSON Report Schema Stability Contract

- `schema_version: "1.0.0"` is included in every JSON report
- All fields present in v1.0.0 are guaranteed to exist in all 1.x releases
- New fields may be added in minor versions (1.1.0, 1.2.0) — consumers must ignore unknown fields
- Breaking changes (removing fields, changing types) require a major version bump (2.0.0)
- `driftscope schema` outputs the Pydantic JSON schema for the current version, enabling downstream consumers to generate typed clients

---

## Provenance Output Schema

When using `--include-provenance`, the JSON report gains a top-level `provenance` field:

```json
{
  "provenance": [
    {
      "file_path": "src/payments/processor.py",
      "line_start": 45,
      "line_end": 67,
      "authorship_class": "ai",
      "originating_commit_sha": "a1b2c3d4e5f6...",
      "commit_timestamp": "2025-11-14T09:23:00Z",
      "co_authorship_tag": "Co-Authored-By: Claude"
    },
    {
      "file_path": "src/payments/processor.py",
      "line_start": 68,
      "line_end": 92,
      "authorship_class": "human",
      "originating_commit_sha": "f6e5d4c3b2a1...",
      "commit_timestamp": "2025-10-30T14:17:00Z",
      "co_authorship_tag": null
    }
  ]
}
```

---

## Testing Strategy

### Unit Tests (~70% of test count)

Each module tested in isolation with typed contracts. No filesystem, no git binary, no network.

| Module | What's tested | Method |
|--------|--------------|--------|
| `authorship/classifier.py` | Every built-in pattern against known commit messages. Custom patterns. `builtin_patterns: false`. Edge: empty message, multi-line body, unicode. | Hardcoded `Commit` fixtures |
| `authorship/patterns.py` | All regex patterns compile. Each pattern matches target and rejects non-matches. | Parameterized pytest |
| `ast_engine/differ.py` | AST diff produces correct add/remove/modify for known before/after source pairs per language. | Inline source strings |
| `ast_engine/survival.py` | Node survives/doesn't survive across scenarios: unchanged, modified, deleted, moved. | Mock `ASTDiff` objects |
| `metrics/survival.py` | Survival rate math. Edge: zero lines, single line, window shorter than commit age. | Pure computation |
| `metrics/complexity.py` | Cyclomatic + cognitive deltas match hand-computed values. Edge: empty function, nested conditionals, switch statements. | Source string fixtures |
| `metrics/churn.py` | Churn attribution percentages for known sequences. Edge: all-human repo, all-AI repo, no churn. | Mock `AttributedHistory` |
| `config/loader.py` | Valid config loads. Invalid raises `ConfigError`. Missing file returns defaults. | YAML strings via `io.StringIO` |
| `reporting/markdown.py` | Output contains expected sections, tables, headers. | String assertion |
| `reporting/json_report.py` | Output validates against Pydantic schema. Round-trip: serialize → parse → validate. | Pydantic validation |

### Integration Tests (~20%)

Test module boundaries with real git repositories and real tree-sitter parsing.

- **Git integration:** Temporary git repo with known commit history via `gitpython` in test setup. Verify blame and log output.
- **Authorship + git:** Commits with co-authorship tags classified correctly from real git output.
- **AST + metrics:** Repo with known Python file, two commits (add + modify). Verify survival rate and complexity delta.
- **Config:** `.driftscope.yaml` with custom patterns in temp repo. `driftscope config validate` reports correct match counts.
- **Cache:** Run analysis twice. Second run uses cache. Cache invalidates on grammar version change.

### E2E Tests (~10%)

Full `driftscope analyze` → `driftscope report` against a fixture repository.

- **Fixture repo:** Synthetic git repo at `tests/fixtures/sample_repo/` with ~50 commits across Python and TypeScript files, including both human and AI-tagged commits, spanning 6 months.
- **E2E scenario 1:** `driftscope analyze --window 90d --format json` produces valid JSON report with non-empty metrics.
- **E2E scenario 2:** `driftscope report --format html --output dashboard.html` produces renderable self-contained HTML.
- **E2E scenario 3:** Idempotency — `driftscope analyze` twice produces identical output.
- **E2E scenario 4:** `driftscope analyze --module src/payments` scopes to single module.
- **E2E scenario 5:** Threshold breach detection — low threshold configured, verify breach reported with `threshold_breaches` field populated. With `--enforce`, verify exit code 2.

### Test Infrastructure

- **pytest** with `pytest-cov`
- `conftest.py` shared fixtures: `temp_git_repo`, `sample_commits`, `sample_config`
- `tests/` mirrors `driftscope/` structure
- No external network calls — all git operations use local temp repos
- Targets: ≥95% line coverage, ≥90% branch coverage, full suite < 5 minutes

---

## Configuration Schema (.driftscope.yaml)

```yaml
authorship:
  builtin_patterns: true
  custom_patterns: []              # additional regexes for AI attribution

analysis:
  languages: [python, typescript, javascript, go, java, ruby]
  exclude_paths:
    - "vendor/**"
    - "**/*.generated.*"
    - "node_modules/**"
  parse_timeout_seconds: 5
  min_lines_per_module: 10

metrics:
  survival_windows: [30d, 90d, 180d, 365d]
  complexity_metrics: [cyclomatic, cognitive]

thresholds:
  enforce: false
  ai_churn_attribution_pct: null   # null = no threshold, set e.g. 50 to flag > 50%
  ai_survival_rate_pct: null       # null = no threshold, set e.g. 50 to flag < 50%

output:
  default_format: markdown

notifications:
  slack_webhook: null              # v1.1 — accepted but produces warning in v1
```

All fields optional. Built-in defaults used when absent.

---

## CLI Contracts

### `driftscope init [PATH]`

- Validates PATH is a git repository (current directory if omitted)
- Checks git binary version ≥ 2.30
- Detects bare repository and configures `git show` mode if needed
- Installs/verifies tree-sitter grammars for configured languages
- Creates `.driftscope.yaml` with defaults if none exists
- Creates `.driftscope/cache.db`
- Exit 0 on success, `ConfigError` or `GitError` on failure

### `driftscope analyze [OPTIONS]`

- `--window 90d` — survival analysis window (default: 90d)
- `--module PATH` — scope to single module, repeatable (default: all modules)
- `--metric survival|complexity-delta|churn|all` — which metrics (default: all)
- `--format json|markdown|html|csv` — output format (default: from config)
- `--output PATH` — write to file instead of stdout
- `--from SHA|DATE` — analysis range start (default: window ago from HEAD)
- `--to SHA` — analysis range end (default: HEAD)
- `--enforce` — exit 2 on threshold breach (default: report only)
- Runs full pipeline: git_client → authorship → ast_engine → metrics → reporting
- Writes cache to `.driftscope/cache.db`
- Exit 0 on success, exit 1 on error, exit 2 on threshold breach (with `--enforce`)

**`--metric complexity-delta` output example (JSON):**

```json
{
  "complexity": {
    "weekly_series": [
      {
        "week_start": "2025-11-04",
        "ai_cyclomatic_mean": 2.3,
        "human_cyclomatic_mean": 0.8,
        "ai_cognitive_mean": 3.1,
        "human_cognitive_mean": 1.2,
        "ai_commit_count": 12,
        "human_commit_count": 34
      }
    ]
  }
}
```

**`--metric complexity-delta` output example (Markdown):**

```markdown
## Complexity Delta — Weekly Trend (365d)

| Week       | AI Cyclomatic | Human Cyclomatic | AI Cognitive | Human Cognitive | AI Commits | Human Commits |
|------------|--------------|------------------|-------------|-----------------|-----------|--------------|
| 2025-11-04 | 2.3          | 0.8              | 3.1         | 1.2             | 12        | 34           |
| 2025-11-11 | 1.9          | 0.6              | 2.7         | 1.0             | 8         | 41           |
```

### `driftscope report [OPTIONS]`

- `--format json|markdown|html|csv` — output format
- `--output PATH` — write to file (required for html)
- `--include-provenance` — add line-level provenance map (see Provenance Output Schema)
- `--baseline DATE` — compare against historical baseline (v1.1)
- Reads from cache (fast) or re-runs analysis if cache stale

### `driftscope diff [FROM_SHA] [TO_SHA]`

- `--format json|markdown` — output format (default: markdown)
- `--module PATH` — scope to single module (repeatable)
- AST-level diff between two commits
- Shows added/removed/modified AST nodes with:
  - Node type (e.g., `function_definition`, `if_statement`)
  - Line range in the file
  - Authorship class of the originating commit
  - Whether the change is AI or human attributed
- Writes diff results to cache for future reference
- Errors: if either SHA doesn't exist → `GitError`; if commits share no files → empty diff, exit 0
- For ad-hoc inspection of a single PR's AI contribution

**Output example (Markdown):**

```markdown
## DriftScope Diff: a1b2c3d..f6e5d4c

### src/payments/processor.py

| Change   | Node Type            | Lines   | Author  |
|----------|---------------------|---------|---------|
| Added    | function_definition | 45-67   | AI      |
| Removed  | if_statement        | 30-34   | Human   |
| Modified | function_definition | 70-92   | AI      |
```

### `driftscope config validate`

- Loads `.driftscope.yaml`
- Validates all fields against Pydantic schema
- Compiles custom regex patterns, reports errors with position
- Runs each pattern against last 100 commits, reports match counts
- Exit 0 if valid, `ConfigError` with details if not

### `driftscope schema`

- Prints current JSON report schema (Pydantic JSON schema) to stdout
- Versioned: `schema_version: "1.0.0"` in every JSON report
- Consumers can use this to generate typed clients

---

## Security Constraints

- No source code or git history transmitted externally — all analysis runs locally
- PAT tokens via environment variables only, never written to disk or included in artifacts
- `.driftscope.yaml` must not accept executable expressions or shell expansion
- All dependencies pinned to exact versions with SHA verification in lock file
- Cache database (`.driftscope/cache.db`) contains git blame data and commit messages — not suitable for commit to public repos; `.driftscope/` should be in `.gitignore`

## Performance Targets

- `driftscope analyze` on 500k LOC / 24-month history: < 15 minutes on 2 vCPU / 7 GB RAM
- Incremental analysis (cached prior run): < 3 minutes for one week of new commits
- tree-sitter parsing: ≥ 50k lines/second per CPU core
- `driftscope init` to first dashboard render on 100k-line repo: ≤ 10 minutes

## Non-Functional Requirements

- **Idempotent:** Same commit range + same git history produces identical output
- **Exit behavior:** Exit 0 on success, exit 1 on error, exit 2 on threshold breach (with `--enforce`)
- **No silent failures:** Never produces incomplete output without signaling
- **Retry-safe:** GitHub Actions weekly runs produce identical output on re-run
- **Bare repo support:** Works on both bare and non-bare git repositories
