# DriftScope

Longitudinal AI code contribution quality monitor. DriftScope analyzes git repositories to track code survival rates, cyclomatic complexity deltas, and churn attribution segmented by human vs. AI contribution — giving teams visibility into how AI-authored code evolves over time.

## What It Does

DriftScope answers questions like:

- What percentage of our codebase was written by AI tools (Copilot, Claude Code, Cursor, Devin)?
- Does AI-authored code survive as long as human-authored code?
- Is AI code introducing more complexity or churn than human code?
- Are quality thresholds being breached in specific modules?

It works by parsing git history, matching co-authorship tags in commit messages, performing AST-level diffing via tree-sitter, and computing module-level metrics.

## Installation

### From PyPI (when published)

```bash
pip install driftscope
```

Or with [uv](https://docs.astral.sh/uv/):

```bash
uv tool install driftscope
```

### From Source

```bash
git clone https://github.com/dgdev25/driftscope.git
cd driftscope

# Install as a global CLI tool (recommended)
uv tool install .

# Or install in editable mode for development
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

### Verify

```bash
driftscope version
# 0.1.0
```

> **Requirements:** Python >= 3.11, Git >= 2.30

## Usage

### 1. Initialize (creates config file)

```bash
cd your-repo
driftscope init
# Created /path/to/your-repo/.driftscope.yaml
```

This creates a `.driftscope.yaml` in your repo with defaults. It tells DriftScope which AI patterns to look for, what languages to parse, and what metrics to compute. You can commit this file — it's repo-specific config.

### 2. Run analysis

```bash
# Print JSON to terminal
driftscope analyze --format json --output -

# Save as Markdown
driftscope analyze --format markdown --output report.md

# Save as HTML
driftscope analyze --format html --output report.html

# Save as CSV
driftscope analyze --format csv --output metrics.csv

# Only analyze commits since a date
driftscope analyze --since 2024-01-01 --format json --output -
```

### 3. Other commands

```bash
driftscope config validate   # Check your .driftscope.yaml for errors
driftscope schema            # Print the JSON report schema
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

```bash
git clone https://github.com/dgdev25/driftscope.git
cd driftscope
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

```bash
pytest                                    # run all 336 tests
pytest --cov=driftscope                   # with coverage
pytest tests/authorship/test_classifier.py # single file
ruff check .                              # lint
mypy driftscope                           # type check
python -m build                           # build sdist + wheel
```

## License

MIT
