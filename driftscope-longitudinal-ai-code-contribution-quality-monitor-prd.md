# DriftScope: Longitudinal AI Code Contribution Quality Monitor — Product Requirements Document

## Executive Summary

Engineering teams adopting AI coding assistants lack objective, longitudinal data on whether AI-generated code survives code review, accumulates technical debt, or degrades module maintainability over time. DriftScope is a CLI tool and GitHub Actions integration that uses AST-level diffing and git authorship attribution to produce weekly dashboards tracking code survival rates, cyclomatic complexity deltas, and churn attribution segmented by human versus AI contribution. It is built for engineering leaders and senior engineers at software-intensive organizations who need evidence-based governance over AI-assisted development workflows.

## Problem Statement

AI coding assistants (GitHub Copilot, Cursor, Claude Code, Devin, and similar tools) are now embedded in daily development workflows at thousands of organizations, yet no standard tooling exists to answer the foundational quality question: *does AI-authored code hold up over time?* Teams operating under AI-assisted development have anecdotal impressions—"Copilot suggestions get reverted a lot" or "the AI-generated modules are harder to maintain"—but no rigorous, continuous measurement to back those impressions up or refute them.

Current alternatives fall short in specific ways:

- **Static linters and code quality tools** (SonarQube, CodeClimate) score code at a point in time but do not track longitudinal survival or attribute quality trends by authorship class.
- **Git analytics platforms** (GitPrime, LinearB, Waydev) focus on developer velocity and throughput, not on the semantic quality or durability of the code itself.
- **Manual audits** are expensive, infrequent, and cannot produce rolling trend data across hundreds of modules.
- **AI vendor dashboards** report acceptance rates (lines accepted at suggestion time) but not post-merge survival, downstream churn, or complexity impact—creating a survivorship bias that flatters AI tooling.

Research (arXiv 2604.00917) has begun quantifying these dynamics at scale, revealing measurable differences in code survival and complexity introduction between human and AI authors. DriftScope operationalizes these research methods into a repeatable, automated engineering workflow so teams do not need a research lab to answer the question for their own repositories.

## Target Users

### Primary

**Engineering Manager / Staff Engineer at a mid-to-large software organization (50–5,000 engineers)** who has rolled out one or more AI coding assistants org-wide and is accountable for code quality and technical debt trends. They run weekly or bi-weekly engineering metrics reviews, interact with tools like Grafana, Datadog, or internal dashboards, and need to report to VPs or CTOs on the ROI and risk profile of AI tooling adoption. Day-to-day they are reviewing PRs, triaging tech debt escalations, and making decisions about tooling policy (which AI tools to allow, how to gate AI-generated code, when to require human review of AI contributions).

### Secondary

- **Platform / DevEx engineers** who own the internal CI/CD toolchain and are responsible for integrating DriftScope into existing pipelines and surfacing its output in existing dashboards.
- **Security and compliance officers** at regulated industries (fintech, healthcare, defense contractors) who need auditability of AI-generated code provenance in the codebase.
- **Open-source maintainers** who want to understand the long-term quality impact of AI-assisted community contributions before merging them into core modules.
- **Researchers and academics** studying AI-assisted software engineering who need a reproducible, configurable measurement tool rather than one-off scripts.

## Goals & Success Metrics

| Goal | Metric | Target (6-month horizon) |
|------|--------|--------------------------|
| Deliver accurate authorship attribution | Precision and recall of AI vs. human label on a labeled benchmark set | ≥ 90% precision, ≥ 85% recall |
| Provide actionable longitudinal quality signal | Percentage of onboarded repos producing ≥ 4 consecutive weekly reports without errors | ≥ 80% of repos |
| Drive adoption in CI/CD pipelines | Number of GitHub Actions workflow integrations activated by paying customers | ≥ 150 within 6 months of GA |
| Achieve time-to-first-insight under 10 minutes | Median wall-clock time from `driftscope init` to first dashboard render on a 100k-line repo | ≤ 10 minutes |
| Demonstrate retention via product stickiness | 30-day retention rate among teams who complete initial setup | ≥ 60% |

## Feature Requirements

### Must Have (v1)

- Parse git history and compute per-line authorship using `git blame` combined with commit message co-authorship tag pattern matching (GitHub Copilot, Claude Code, Cursor, and configurable custom patterns).
- Generate AST-level diffs per commit using tree-sitter grammars for Python, TypeScript/JavaScript, Go, Java, and Ruby, enabling semantic line survival tracking that is not fooled by pure whitespace or formatting changes.
- Compute AI-authored line survival rate at configurable windows (30-day, 90-day, 180-day, 365-day) per repository module.
- Compute cyclomatic complexity delta per commit segmented by author type (human vs. AI), surfaced at function, file, and module granularity.
- Compute module-level churn attribution over rolling 365-day windows, showing the percentage of churn traceable to AI-introduced code.
- Expose a CLI (`driftscope`) supporting `init`, `analyze`, `report`, and `diff` subcommands with JSON and Markdown output modes.
- Provide a GitHub Actions workflow YAML that runs DriftScope analysis on PR merge and on a scheduled weekly cron, uploading results as build artifacts and optionally failing the workflow when configurable quality thresholds are breached.
- Generate a weekly Markdown/HTML maintainability trend dashboard per repository module, renderable as a GitHub Pages site or standalone HTML file.
- Support repositories hosted on GitHub (cloud and GHES) with PAT-based authentication.
- Produce a machine-readable JSON report schema versioned under semantic versioning so downstream consumers can build on stable contracts.

### Should Have (v1.1)

- Support GitLab (cloud and self-hosted) as a repository host with equivalent CI integration.
- Add tree-sitter grammars for Rust, C/C++, and Swift to expand language coverage.
- Implement a web-based interactive dashboard (single-page app) consumable from the CLI output, replacing static HTML.
- Provide Slack and Microsoft Teams webhook notifications on weekly report generation or threshold breach events.
- Add a `--baseline` flag allowing teams to compare current windows against a user-defined historical baseline date rather than only rolling periods.
- Support monorepo configurations with per-package or per-service scoping to avoid cross-module noise.
- Publish pre-built Docker images for the CLI to simplify CI integration without requiring local language runtime dependencies.
- Add CSV export for all metrics tables to enable import into BI tools (Tableau, Looker, Metabase).

### Won't Have (this version)

- **Real-time PR annotation / inline review bot:** Requires tight GitHub App permissions model and latency guarantees beyond v1 scope; deferred to v2.
- **IDE plugin (VS Code, JetBrains):** Substantially different distribution and UX surface from the CLI/CI core; would dilute v1 focus.
- **Multi-repository fleet aggregation dashboard:** Cross-repo rollup requires a hosted backend and data persistence layer; v1 is fully local/self-hosted to reduce security friction during early adoption.
- **AI model identification (which specific LLM generated the code):** Attribution below the human/AI binary is unreliable with current metadata; claiming this capability would undermine trust in the tool.
- **Automatic remediation or refactoring suggestions:** Out of scope for a measurement tool; risks scope creep into a separate product category.

## User Stories

---

**As an** engineering manager, **I want to** run a single CLI command against our main repository and receive a report showing the 90-day survival rate of AI-authored lines broken down by module **so that** I can identify which modules are accumulating AI-generated code that does not survive review and prioritize focused technical debt reduction there.

*Acceptance criteria:*
- `driftscope analyze --window 90d --format markdown` completes without error on a repository with 12 months of git history.
- Output contains a per-module table with columns: module path, AI-authored lines introduced, AI-authored lines surviving at window end, survival rate percentage.
- Modules with fewer than a configurable minimum line threshold are excluded from the report to suppress noise.
- Report includes a timestamp, repository name, and the commit SHA range analyzed.

---

**As a** platform engineer, **I want to** add DriftScope to our GitHub Actions merge pipeline **so that** every PR merge automatically updates our quality trend data and posts a summary comment to the PR without requiring manual intervention.

*Acceptance criteria:*
- The provided GitHub Actions workflow YAML installs and runs DriftScope with no additional configuration beyond a PAT secret.
- A PR comment is posted summarizing the AI-authored lines in the PR, their projected churn risk based on module history, and a link to the full report artifact.
- The workflow completes in under 5 minutes for PRs touching fewer than 500 files.
- The workflow step is idempotent: re-running on the same commit produces identical output.

---

**As a** staff engineer, **I want to** see the cyclomatic complexity delta introduced by AI-authored commits versus human-authored commits over the past year for our payments module **so that** I can make an evidence-based case to leadership that our AI tooling policy needs tighter review requirements for that module.

*Acceptance criteria:*
- `driftscope analyze --module src/payments --metric complexity-delta --window 365d` produces a time-series output with weekly data points.
- Each data point shows mean cyclomatic complexity delta for AI commits and human commits that week.
- Output is available in both human-readable Markdown and machine-readable JSON.
- The tool documents its complexity calculation method (which AST node types contribute to cyclomatic complexity per language) in the report.

---

**As a** security officer at a regulated financial institution, **I want to** export a full audit trail of which lines of code in our production branch were AI-generated and have never been modified by a human reviewer **so that** I can satisfy an internal audit requirement for AI code provenance.

*Acceptance criteria:*
- `driftscope report --format json --include-provenance` outputs a line-level provenance map for the HEAD commit of a specified branch.
- Each entry includes: file path, line range, authorship class (human/AI), originating commit SHA, commit timestamp, and co-authorship tag matched (if AI).
- The JSON output validates against the published DriftScope report schema.
- The command completes without requiring network access beyond the local git repository.

---

**As an** open-source maintainer, **I want to** configure DriftScope to recognize my project-specific AI contribution conventions (e.g., a custom `AI-Generated:` trailer in commit messages) **so that** the authorship attribution correctly reflects our community's tagging practices rather than defaulting to generic patterns.

*Acceptance criteria:*
- A `.driftscope.yaml` configuration file in the repository root accepts a `authorship.ai_patterns` list of regular expressions matched against commit message bodies and trailers.
- Custom patterns are applied in addition to, not instead of, the built-in patterns unless `authorship.builtin_patterns: false` is set.
- Running `driftscope config validate` confirms the configuration is syntactically valid and reports the number of commits matched by each pattern against recent history.
- Documentation covers the five most common AI tool commit message conventions out of the box.

---

**As an** engineering manager, **I want to** receive a weekly email or Slack digest summarizing the top-5 modules by AI churn attribution change week-over-week **so that** I can stay informed of emerging quality hotspots without manually running the CLI.

*Acceptance criteria:*
- The GitHub Actions scheduled workflow supports a `notifications.slack_webhook` configuration key.
- The Slack message includes: top-5 modules ranked by week-over-week AI churn attribution increase, a sparkline-style text trend, and a link to the full HTML dashboard.
- The notification fires only when there is a statistically meaningful change (configurable threshold, default ≥ 5 percentage points) to reduce noise.
- Notification delivery failure does not cause the workflow to fail.

## Non-Functional Requirements

- **Performance:** `driftscope analyze` on a repository with 500k lines of code and 24 months of git history must complete in under 15 minutes on a standard GitHub Actions runner (2 vCPU, 7 GB RAM). Incremental analysis on repositories with a cached prior run must complete in under 3 minutes for a week's worth of new commits. Tree-sitter parsing must process at least 50k lines per second per CPU core.
- **Security:** No source code or git history is transmitted to any external server; all analysis runs locally within the user's environment. PAT tokens are consumed via standard environment variable injection and are never written to disk or included in output artifacts. The `.driftscope.yaml` configuration file must not accept executable expressions or shell expansion to prevent injection via repository-committed config. Dependency supply chain: all dependencies pinned to exact versions with SHA verification in the lock file.
- **Scalability:** v1 targets single-repository analysis for repositories up to 2 million lines of code and 5 years of git history. The JSON report schema must accommodate repositories with up to 10,000 modules without breaking downstream consumers. The GitHub Actions integration must support repositories with up to 50 concurrent workflow runs without contention on shared resources.
- **Reliability:** The CLI must exit with a non-zero status code and a machine-readable error payload on any failure; it must never silently produce incomplete output. The GitHub Actions workflow must surface analysis errors as workflow annotations, not silent failures. Weekly scheduled runs must be retry-safe: re-running the same analysis window produces identical output given the same git history.

## Integration & Compatibility

- **Git:** Local git binary (≥ 2.30) via subprocess; no libgit2 dependency to avoid version matrix complexity. Supports bare and non-bare repositories.
- **GitHub (cloud and GHES ≥ 3.8):** GitHub Actions runner environment, GitHub REST API v3 for PR comment posting, GitHub Pages for dashboard deployment. Authentication via `GITHUB_TOKEN` or PAT.
- **tree-sitter:** Language grammars for Python, TypeScript, JavaScript, Go, Java, Ruby fetched as versioned compiled WASM/native binaries at tool installation time; grammar versions pinned per DriftScope release.
- **Co-authorship tag formats:** GitHub Copilot (`Co-Authored-By: GitHub Copilot`), Cursor AI, Claude Code (`Co-Authored-By: Claude`), Devin, and generic `AI-Generated:` trailers. Configurable via `.driftscope.yaml`.
- **Output formats:** Markdown (GitHub-flavored), HTML (self-contained single file, no CDN dependencies), JSON (versioned schema, available at `driftscope schema`), CSV (tabular metrics only).
- **CI systems:** GitHub Actions (v1 first-class). Docker image provided for use in any CI system that supports containers (GitLab CI, CircleCI, Jenkins, Buildkite) as a best-effort compatibility path.
- **Notification sinks (v1.1):** Slack Incoming Webhooks, Microsoft Teams Incoming Webhooks.
- **Package distribution:** PyPI (Python package with compiled tree-sitter bindings), Homebrew tap, direct binary download via GitHub Releases (Linux x86_64, Linux arm64, macOS arm64).

## Open Questions

1. **Authorship classification boundary:** The human/AI binary is clear for commits with standard co-authorship tags, but a large fraction of real-world AI-assisted commits carry no tags (developers accept suggestions without attribution). Should DriftScope attempt probabilistic attribution using commit message style signals, or should untagged commits always be classified as human, accepting a systematic undercount of AI contribution? The answer affects precision/recall tradeoffs and must be validated against a labeled dataset before v1 ships.

2. **AST survival definition:** "Line survival" at the AST level can mean (a) the AST node introduced by the commit is still present at window end, (b) the enclosing function is still present and unmodified, or (c) the enclosing module still has the node reachable. These definitions produce materially different survival rates for refactored code. The v1 definition must be locked and documented before the report schema is published, as changing it will break comparability across releases.

3. **Complexity metric selection:** Cyclomatic complexity is well-understood but has known limitations (it does not capture cognitive load, nesting depth, or API surface area). Should v1 expose only cyclomatic complexity, or should it also include cognitive complexity (as defined by SonarSource) and Halstead volume? Adding more metrics increases implementation and communication complexity; shipping only cyclomatic complexity risks being dismissed as too narrow by sophisticated users.

4. **Privacy and legal exposure for enterprise customers:** Some organizations may have policies or jurisdictional requirements that prohibit writing git blame output or commit message content to disk in CI artifacts, even locally. Should DriftScope offer a `--no-persist-metadata` mode that computes metrics in-memory only and never writes intermediate authorship data to the filesystem? This would require an architecture change to the analysis pipeline and needs legal/compliance input from design partners before the architecture is finalized.

5. **Threshold policy enforcement model:** The GitHub Actions integration can optionally fail a workflow when AI churn attribution exceeds a threshold. This is a high-stakes behavior: a misconfigured threshold could block legitimate merges. Should threshold enforcement be opt-in (default: report only, never fail) with an explicit `--enforce` flag, or opt-out (default: enforce, disable with `--no-enforce`)? The choice signals the product's default stance on AI code governance and will be highly visible to early adopters.

---
*This PRD is derived from the research context and should be treated as a starting point for validation, not a final specification.*