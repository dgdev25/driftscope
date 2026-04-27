# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

DriftScope is a CLI tool and GitHub Actions integration for longitudinal tracking of AI-authored code quality in git repositories. It uses AST-level diffing (tree-sitter) and git authorship attribution to produce dashboards tracking code survival rates, cyclomatic complexity deltas, and churn attribution segmented by human vs. AI contribution.

The full PRD is at `driftscope-longitudinal-ai-code-contribution-quality-monitor-prd.md`.

## Architecture (Planned)

### CLI (`driftscope`)
- **Subcommands:** `init`, `analyze`, `report`, `diff`, `config validate`, `schema`
- **Output formats:** Markdown (GFM), HTML (self-contained), JSON (versioned schema), CSV
- **Configuration:** `.driftscope.yaml` in repo root — AI authorship patterns, thresholds, module scoping

### Analysis Pipeline
1. **Git history parsing** — `git blame` + commit message co-authorship tag matching (Copilot, Cursor, Claude Code, Devin, custom patterns)
2. **AST diffing** — tree-sitter grammars for Python, TypeScript/JavaScript, Go, Java, Ruby
3. **Metric computation** — line survival rates (30/90/180/365-day windows), cyclomatic complexity deltas, module-level churn attribution
4. **Report generation** — weekly Markdown/HTML dashboards, JSON reports with versioned schema

### Key Architectural Constraints
- All analysis runs locally — no source code or git history transmitted externally
- PAT tokens via environment variables only, never written to disk
- No libgit2 dependency — uses local git binary (≥ 2.30) via subprocess
- tree-sitter grammars fetched as versioned compiled binaries at install time
- Idempotent: re-running on the same commit produces identical output
- CLI must exit non-zero with machine-readable error payload on failure (never silent incomplete output)

### GitHub Actions Integration
- Runs on PR merge and scheduled weekly cron
- Uploads results as build artifacts
- Optionally fails workflow on configurable quality threshold breaches
- Posts PR summary comments via GitHub REST API v3

### Planned Language Support (v1)
Python, TypeScript/JavaScript, Go, Java, Ruby

### Planned Distribution
PyPI, Homebrew tap, GitHub Releases (Linux x86_64, Linux arm64, macOS arm64), Docker image

## Implementation Status

Pre-implementation. Only the PRD exists. No source code, build system, or tests yet.
