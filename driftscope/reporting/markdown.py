"""Markdown (GFM) report renderer — produces a human-readable report.

Time Complexity: O(n) where n is the number of modules.
Space Complexity: O(n) for the output string.
"""

from __future__ import annotations

from driftscope.models.report import MetricsResult


def render_markdown(result: MetricsResult) -> str:
    """Render a MetricsResult as a GitHub-Flavored Markdown report.

    Sections: header, executive summary, survival table, complexity table,
    churn table, threshold breaches, skipped files, metadata.

    Args:
        result: The analysis result to render.

    Returns:
        A GFM-formatted markdown string.
    """
    parts: list[str] = []
    start = result.range_start.strftime("%Y-%m-%d")
    end = result.range_end.strftime("%Y-%m-%d")

    # Header
    parts.append(f"# DriftScope Report")
    parts.append(f"**Analysis Period:** {start} to {end}")
    parts.append("")

    # Executive summary
    total_modules = len(result.modules)
    total_lines = sum(m.total_lines for m in result.modules)
    ai_lines = sum(m.ai_lines for m in result.modules)
    human_lines = sum(m.human_lines for m in result.modules)
    ai_pct = (ai_lines / total_lines * 100) if total_lines > 0 else 0.0

    parts.append("## Executive Summary")
    parts.append("")
    parts.append(f"| Metric | Value |")
    parts.append(f"|--------|-------|")
    parts.append(f"| Total Modules | {total_modules} |")
    parts.append(f"| Total Lines | {total_lines} |")
    parts.append(f"| AI Lines | {ai_lines} |")
    parts.append(f"| Human Lines | {human_lines} |")
    parts.append(f"| AI Attribution % | {ai_pct:.1f}% |")
    parts.append("")

    # Survival table
    parts.append("## Survival Rates")
    parts.append("")
    parts.append("| Module | Window | AI Rate | Human Rate |")
    parts.append("|--------|--------|---------|------------|")
    for mod in result.modules:
        for window_key in sorted(mod.survival.keys()):
            sm = mod.survival[window_key]
            parts.append(
                f"| {mod.module_path} | {sm.window} | "
                f"{sm.ai_survival_rate:.1%} | {sm.human_survival_rate:.1%} |"
            )
    parts.append("")

    # Complexity table
    parts.append("## Complexity Deltas")
    parts.append("")
    parts.append(
        "| Module | AI Cyclomatic Δ | Human Cyclomatic Δ | "
        "AI Cognitive Δ | Human Cognitive Δ |"
    )
    parts.append(
        "|--------|-------------------|----------------------|"
    "-------------------|----------------------|"
    )
    for mod in result.modules:
        c = mod.complexity
        parts.append(
            f"| {mod.module_path} | {c.cyclomatic_delta_ai:.1f} | "
            f"{c.cyclomatic_delta_human:.1f} | {c.cognitive_delta_ai:.1f} | "
            f"{c.cognitive_delta_human:.1f} |"
        )
    parts.append("")

    # Churn table
    parts.append("## Churn Attribution")
    parts.append("")
    parts.append("| Module | Total Churn | AI Churn | AI Attribution % |")
    parts.append("|--------|-------------|----------|------------------|")
    for mod in result.modules:
        ch = mod.churn
        parts.append(
            f"| {mod.module_path} | {ch.total_churn_lines} | "
            f"{ch.ai_churn_lines} | {ch.ai_churn_attribution_pct:.1f}% |"
        )
    parts.append("")

    # Threshold breaches
    parts.append("## Threshold Breaches")
    parts.append("")
    if result.threshold_breaches:
        parts.append("| Metric | Module | Value | Threshold | Direction |")
        parts.append("|--------|--------|-------|-----------|-----------|")
        for breach in result.threshold_breaches:
            parts.append(
                f"| {breach.metric} | {breach.module_path} | "
                f"{breach.value} | {breach.threshold} | {breach.direction} |"
            )
    else:
        parts.append("No threshold breaches detected.")
    parts.append("")

    # Skipped files
    parts.append("## Skipped Files")
    parts.append("")
    if result.skipped_files:
        parts.append("| File | Reason |")
        parts.append("|------|--------|")
        for sf in result.skipped_files:
            parts.append(f"| {sf.get('file', 'unknown')} | {sf.get('reason', 'N/A')} |")
    else:
        parts.append("No skipped files.")
    parts.append("")

    # Metadata
    parts.append("## Metadata")
    parts.append("")
    parts.append(f"- Schema Version: {result.schema_version}")
    parts.append(f"- Repository: `{result.repo_path}`")
    parts.append(f"- Commit Range: `{result.commit_range[0]}` .. `{result.commit_range[1]}`")
    if result.data_incomplete:
        parts.append("- **Note:** Analysis data is incomplete.")

    return "\n".join(parts) + "\n"
