"""Complexity metric computation — cyclomatic and cognitive complexity deltas.

Provides functions to count decision points in source code and compute
per-module complexity deltas segmented by authorship (AI vs. human),
along with weekly time-series aggregation.

Time Complexity:
    - count_cyclomatic: O(n) where n = lines of source
    - count_cognitive:  O(n * d) where d = max nesting depth
    - compute_complexity_metrics: O(D * C) where D = diffs, C = avg changes per diff
"""

from __future__ import annotations

import re
from collections import defaultdict
from datetime import date

from driftscope.metrics._helpers import module_of
from driftscope.models.ast_diff import ASTDiffSet, ASTFileDiff
from driftscope.models.metrics import ComplexityMetrics, WeeklyComplexity


# ---------------------------------------------------------------------------
# Cyclomatic complexity patterns
# ---------------------------------------------------------------------------

_CYCLOMATIC_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\bif\b"),
    re.compile(r"\belif\b"),
    re.compile(r"\bfor\b"),
    re.compile(r"\bwhile\b"),
    re.compile(r"\band\b"),
    re.compile(r"\bor\b"),
    re.compile(r"\bexcept\b"),
    re.compile(r"\bwith\b"),
    re.compile(r"\bassert\b"),
    re.compile(r"\?"),          # ternary in C-style languages
    re.compile(r"\bif\b.*\belse\b"),  # ternary expression: x if cond else y
]


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------

def count_cyclomatic(source: str) -> int:
    """Count cyclomatic complexity decision points in *source*.

    Scans for control-flow keywords and boolean operators using a set of
    compiled regular expressions.  Each match contributes +1 to the total.

    Args:
        source: Full source text of a file or code fragment.

    Returns:
        Number of decision points found (>= 0).

    Time Complexity: O(n) where n = len(source).
    """
    total = 0
    for pattern in _CYCLOMATIC_PATTERNS:
        total += len(pattern.findall(source))
    return total


def count_cognitive(source: str) -> int:
    """Count cognitive complexity in *source*.

    Starts from the cyclomatic base and adds an increment for each
    decision point equal to its nesting depth (1-indexed).  This penalises
    deeply nested control flow.

    Args:
        source: Full source text of a file or code fragment.

    Returns:
        Cognitive complexity score (>= cyclomatic base).

    Time Complexity: O(n * d) where n = lines, d = max nesting depth.
    """
    base = count_cyclomatic(source)
    nesting = 0
    increment = 0
    for line in source.splitlines():
        stripped = line.rstrip()
        if not stripped:
            continue
        # Heuristic: decrease nesting on dedent
        indent = len(line) - len(line.lstrip())
        # Track rough nesting level (4-space convention)
        nesting = indent // 4
        # If line contains a decision keyword, add nesting penalty
        for pattern in _CYCLOMATIC_PATTERNS:
            if pattern.search(stripped):
                increment += nesting
                break  # count each line's nesting contribution once
    return base + increment


# ---------------------------------------------------------------------------
# Module-level complexity metrics
# ---------------------------------------------------------------------------

def compute_complexity_metrics(
    diff_set: ASTDiffSet,
    commit_weeks: dict[str, date],
) -> dict[str, ComplexityMetrics]:
    """Compute complexity delta metrics per module.

    Groups AST diffs by their top-level directory module, computes cyclomatic
    and cognitive complexity deltas for AI and human authorship, and builds a
    weekly time series.

    Args:
        diff_set: Collection of AST file diffs across commits.
        commit_weeks: Mapping of commit SHA to the ISO week start date.

    Returns:
        Dict mapping module name to ComplexityMetrics.  Empty dict if
        *diff_set* has no diffs.

    Time Complexity: O(D * C) where D = diffs, C = avg changes per diff.
    """
    if not diff_set.diffs:
        return {}

    # Group diffs by module
    module_diffs: dict[str, list[ASTFileDiff]] = defaultdict(list)
    for diff in diff_set.diffs:
        module = module_of(diff.file_path)
        module_diffs[module].append(diff)

    result: dict[str, ComplexityMetrics] = {}
    for module, diffs in module_diffs.items():
        ai_cyclomatic_deltas: list[float] = []
        human_cyclomatic_deltas: list[float] = []
        ai_cognitive_deltas: list[float] = []
        human_cognitive_deltas: list[float] = []

        # Weekly aggregation data
        weekly_data: dict[date, dict[str, list[float]]] = defaultdict(
            lambda: {"ai_cyclo": [], "human_cyclo": [], "ai_cog": [], "human_cog": [], "ai_commits": set(), "human_commits": set()}
        )

        for diff in diffs:
            # Count complexity from node_types of added changes.
            # node_types contain language-specific names (e.g. "if_statement",
            # "for_statement") so we join them for keyword scanning.
            added_nodes = [ch for ch in diff.changes if ch.change_type == "added"]
            node_text = " ".join(ch.node_type.replace("_", " ") for ch in added_nodes)
            cyclo = count_cyclomatic(node_text)
            cog = count_cognitive(node_text)

            if diff.authorship_class == "ai":
                ai_cyclomatic_deltas.append(float(cyclo))
                ai_cognitive_deltas.append(float(cog))
            else:
                human_cyclomatic_deltas.append(float(cyclo))
                human_cognitive_deltas.append(float(cog))

            # Weekly series aggregation
            week = commit_weeks.get(diff.commit_sha)
            if week is not None:
                bucket = weekly_data[week]
                if diff.authorship_class == "ai":
                    bucket["ai_cyclo"].append(float(cyclo))
                    bucket["ai_cog"].append(float(cog))
                    bucket["ai_commits"].add(diff.commit_sha)
                else:
                    bucket["human_cyclo"].append(float(cyclo))
                    bucket["human_cog"].append(float(cog))
                    bucket["human_commits"].add(diff.commit_sha)

        result[module] = ComplexityMetrics(
            cyclomatic_delta_ai=sum(ai_cyclomatic_deltas),
            cyclomatic_delta_human=sum(human_cyclomatic_deltas),
            cognitive_delta_ai=sum(ai_cognitive_deltas),
            cognitive_delta_human=sum(human_cognitive_deltas),
            weekly_series=_build_weekly_series(weekly_data),
        )

    return result


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _build_weekly_series(
    weekly_data: dict[date, dict[str, list[float] | set[str]]],
) -> list[WeeklyComplexity]:
    """Build sorted weekly complexity time series.

    Args:
        weekly_data: Mapping of week start date to accumulated complexity
            deltas and commit SHAs per authorship class.

    Returns:
        Chronologically sorted list of WeeklyComplexity entries.

    Time Complexity: O(W) where W = number of unique weeks.
    """
    series: list[WeeklyComplexity] = []
    for week_start in sorted(weekly_data):
        bucket = weekly_data[week_start]
        ai_cyclo = bucket["ai_cyclo"]
        human_cyclo = bucket["human_cyclo"]
        ai_cog = bucket["ai_cog"]
        human_cog = bucket["human_cog"]
        series.append(
            WeeklyComplexity(
                week_start=week_start,
                ai_cyclomatic_mean=sum(ai_cyclo) / len(ai_cyclo) if ai_cyclo else 0.0,
                human_cyclomatic_mean=sum(human_cyclo) / len(human_cyclo) if human_cyclo else 0.0,
                ai_cognitive_mean=sum(ai_cog) / len(ai_cog) if ai_cog else 0.0,
                human_cognitive_mean=sum(human_cog) / len(human_cog) if human_cog else 0.0,
                ai_commit_count=len(bucket["ai_commits"]),
                human_commit_count=len(bucket["human_commits"]),
            )
        )
    return series
