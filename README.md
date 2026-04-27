# DriftScope

Longitudinal AI code contribution quality monitor. DriftScope analyzes git repositories to track code survival rates, cyclomatic complexity deltas, and churn attribution segmented by human vs. AI contribution — giving teams visibility into how AI-authored code evolves over time.

## What It Does

DriftScope answers questions like:

- What percentage of our codebase was written by AI tools (Copilot, Claude Code, Cursor, Devin)?
- Does AI-authored code survive as long as human-authored code?
- Is AI code introducing more complexity or churn than human code?
- Are quality thresholds being breached in specific modules?

It works by parsing git history, matching co-authorship tags in commit messages, performing AST-level diffing via tree-sitter, and computing module-level metrics.

## Quick Start

### Install

```bash
pip install driftscope
```

Or with [uv](https://docs.astral.sh/uv/):

```bash
uv tool install driftscope
```

### Initialize

```bash
cd your-repo
driftscope init
```

This creates a `.driftscope.yaml` config file with sensible defaults.

### Analyze

```bash
# JSON to stdout
driftscope analyze --format json --output -

# Markdown report
driftscope analyze --format markdown --output report.md

# HTML dashboard
driftscope analyze --format html --output report.html

# CSV for spreadsheet import
driftscope analyze --format csv --output metrics.csv

# Analyze a specific time window
driftscope analyze --since 2024-01-01 --until 2024-06-01 --format json --output -
```

### Validate Config

```bash
driftscope config validate
```

### View Report Schema

```bash
driftscope schema
```

## CLI Reference

```
driftscope [OPTIONS] COMMAND [ARGS]

Commands:
  init              Create a default .driftscope.yaml config file
  analyze           Run the full analysis pipeline and produce a report
  config validate   Validate a .driftscope.yaml config file
  schema            Print the JSON schema for report output
  version           Print the DriftScope version

Analyze Options:
  --repo-path TEXT    Path to the git repository root (default: cwd)
  --since TEXT        ISO 8601 date for start of analysis window
  --until TEXT        ISO 8601 date for end of analysis window
  --format TEXT       Output format: json, markdown, html, csv (default: json)
  --output TEXT       Output file path, or '-' for stdout
  --config TEXT       Path to .driftscope.yaml config file
```

## Configuration

DriftScope uses `.driftscope.yaml` in the repository root. Run `driftscope init` to create one with defaults.

```yaml
authorship:
  builtin_patterns: true          # Match Copilot, Claude, Cursor, Devin
  custom_patterns: []             # Add your own AI tool patterns

analysis:
  languages:                      # AST parsing targets
    - python
    - typescript
    - javascript
    - go
    - java
    - ruby
  exclude_paths:                  # Glob patterns to skip
    - vendor/**
    - "**/*.generated.*"
    - node_modules/**
  parse_timeout_seconds: 5.0
  min_lines_per_module: 10

metrics:
  survival_windows:               # Track code survival over these periods
    - 30d
    - 90d
    - 180d
    - 365d
  complexity_metrics:
    - cyclomatic
    - cognitive

thresholds:
  enforce: false                  # Set true to fail CI on breach
  ai_churn_attribution_pct: null
  ai_survival_rate_pct: null

output:
  default_format: markdown
```

### Custom AI Patterns

Add patterns to match your team's AI tools:

```yaml
authorship:
  builtin_patterns: true
  custom_patterns:
    - name: "MyAI"
      email: "ai@mycompany.com"
    - name: "Aider"
      email: "noreply@aider.chat"
```

Patterns match against `Co-authored-by:` trailers in commit messages.

## How It Works

### Pipeline

```
Git History ──► Commit Classification ──► AST Diffing ──► Metric Computation ──► Report
     │                  │                       │                │
  git log         co-author tag          tree-sitter        survival rate
  git blame       pattern matching       node-level diff    complexity delta
                                                           churn attribution
```

1. **Git History Parsing** — `git log` + `git blame` via subprocess (no libgit2 dependency)
2. **Authorship Classification** — Matches `Co-authored-by:` tags against configurable patterns (Copilot, Claude Code, Cursor, Devin, custom)
3. **AST Diffing** — tree-sitter grammars for Python, TypeScript/JS, Go, Java, Ruby
4. **Metric Computation** — Line survival rates, cyclomatic/cognitive complexity deltas, module-level churn attribution
5. **Report Generation** — JSON (versioned schema), Markdown (GFM), HTML (self-contained), CSV

### Key Properties

- **Local-only** — No source code or git history is transmitted externally
- **Idempotent** — Re-running on the same commit produces identical output
- **Cache-backed** — SQLite WAL cache avoids redundant AST parsing
- **Fail-safe** — Exits non-zero with machine-readable JSON error payload on failure

## GitHub Actions Integration

### PR Comment on Merge

```yaml
# .github/workflows/driftscope.yml
name: DriftScope
on:
  pull_request:
    types: [closed]
  schedule:
    - cron: '0 9 * * 1'  # Weekly Monday 9am

jobs:
  analyze:
    if: github.event.pull_request.merged == true || github.event_name == 'schedule'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - uses: actions/setup-python@v5
        with:
          python-version: '3.13'
      - run: pip install driftscope
      - run: driftscope analyze --format json --output driftscope-report.json
      - run: driftscope analyze --format markdown --output driftscope-report.md
      - name: Post PR comment
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          python -c "
          from driftscope.integrations.github_pr import post_pr_comment
          from pathlib import Path
          post_pr_comment(Path('driftscope-report.json'), report_url='${{ github.server_url }}/${{ github.repository }}/actions/runs/${{ github.run_id }}')
          "
      - uses: actions/upload-artifact@v4
        with:
          name: driftscope-report
          path: driftscope-report.*
```

Required environment variables for PR comment posting:

| Variable | Source |
|---|---|
| `GITHUB_REPOSITORY` | Automatic in Actions (`owner/repo`) |
| `GITHUB_REF` | Automatic in Actions (`refs/pull/N/merge`) |
| `GITHUB_TOKEN` | Automatic in Actions |

## Output Formats

### JSON

Versioned schema with full metric data. Use `driftscope schema` to view the schema.

```json
{
  "schema_version": "1.0",
  "repo_path": "/path/to/repo",
  "commit_range": ["abc123", "def456"],
  "range_start": "2024-01-15T10:00:00Z",
  "range_end": "2024-06-01T10:00:00Z",
  "modules": [
    {
      "module_path": "src/payments",
      "total_lines": 150,
      "ai_lines": 45,
      "human_lines": 105,
      "survival": { ... },
      "complexity": { ... },
      "churn": { ... }
    }
  ],
  "skipped_files": [],
  "threshold_breaches": []
}
```

### Markdown

GFM-formatted report with tables and sections — suitable for PR comments, Slack, or documentation.

### HTML

Self-contained HTML file with inline CSS. No external dependencies — works offline.

### CSV

Flat table with one row per module. Headers: `module`, `total_lines`, `ai_lines`, `human_lines`, and metric columns.

## Development

### Setup

```bash
git clone https://github.com/dgdev25/driftscope.git
cd driftscope
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

### Run Tests

```bash
# Full suite
pytest

# With coverage
pytest --cov=driftscope --cov-report=term-missing

# Unit tests only (skip E2E)
pytest --ignore=tests/e2e

# Single test file
pytest tests/authorship/test_classifier.py

# Verbose
pytest -v
```

### Lint & Type Check

```bash
ruff check .
ruff format --check .
mypy driftscope
```

### Build

```bash
pip install build
python -m build
```

### Docker

```bash
docker build -t driftscope .
docker run -v /path/to/repo:/repo driftscope analyze --repo-path /repo --format json --output -
```

## Architecture

```
driftscope/
├── ast_engine/         # tree-sitter parsing, AST diffing, node survival
│   ├── parser.py       # Language-aware source parsing
│   ├── differ.py       # AST-level diff computation
│   └── survival.py     # Node survival tracking
├── authorship/         # AI vs human commit classification
│   ├── patterns.py     # Co-authorship tag pattern matching
│   └── classifier.py   # Commit history classification
├── cache/              # SQLite-backed analysis cache (WAL)
│   └── manager.py
├── cli/                # Typer CLI interface
│   ├── app.py          # Command definitions
│   └── main.py         # Entry point re-export
├── config/             # Pydantic v2 config schema + YAML loader
│   ├── schema.py
│   └── loader.py
├── git_client/         # Git operations via subprocess
│   ├── log.py          # git log parsing
│   ├── blame.py        # git blame parsing
│   └── diff_parser.py  # Unified diff parsing
├── integrations/       # External service integrations
│   └── github_pr.py    # PR comment posting via REST API v3
├── metrics/            # Metric computation
│   ├── survival.py     # Line survival rates (30/90/180/365d windows)
│   ├── complexity.py   # Cyclomatic/cognitive complexity deltas
│   └── churn.py        # Module-level churn attribution
├── models/             # Pydantic v2 data models
│   ├── commit.py       # Commit, AttributedCommit
│   ├── history.py      # CommitHistory, AttributedHistory
│   ├── metrics.py      # ModuleMetrics, SurvivalMetrics, etc.
│   ├── report.py       # MetricsResult (top-level report)
│   └── ...
├── reporting/          # Output renderers
│   ├── json_report.py
│   ├── markdown.py
│   ├── html.py
│   └── csv_export.py
└── errors.py           # DriftScopeError hierarchy
```

## Requirements

- Python >= 3.11
- Git >= 2.30

## License

MIT
