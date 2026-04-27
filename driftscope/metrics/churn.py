"""Churn metric computation — module-level churn attribution.

Counts total added/removed lines and AI-attributed churn per module,
producing an AI churn attribution percentage.

Time Complexity:
    - compute_churn_metrics: O(D * C) where D = diffs, C = changes per diff
"""

from __future__ import annotations

from collections import defaultdict

from driftscope.metrics._helpers import module_of
from driftscope.models.ast_diff import ASTDiffSet
from driftscope.models.metrics import ChurnMetrics


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def compute_churn_metrics(diff_set: ASTDiffSet) -> dict[str, ChurnMetrics]:
    """Compute churn attribution metrics per module.

    For each module, counts total churn lines (added + removed) and
    AI-attributed churn lines, then computes the AI churn attribution
    percentage.

    Args:
        diff_set: Collection of AST file diffs across commits.

    Returns:
        Dict mapping module name to ChurnMetrics.  Returns empty dict
        if *diff_set* has no diffs.

    Time Complexity: O(D * C) where D = diffs, C = changes per diff.
    """
    if not diff_set.diffs:
        return {}

    # Accumulate churn counts per module
    module_data: dict[str, dict[str, int]] = defaultdict(
        lambda: {"total_added": 0, "total_removed": 0, "ai_added": 0, "ai_removed": 0}
    )

    for diff in diff_set.diffs:
        module = module_of(diff.file_path)
        bucket = module_data[module]

        for change in diff.changes:
            if change.change_type == "added":
                bucket["total_added"] += 1
                if diff.authorship_class == "ai":
                    bucket["ai_added"] += 1
            elif change.change_type == "removed":
                bucket["total_removed"] += 1
                if diff.authorship_class == "ai":
                    bucket["ai_removed"] += 1

    result: dict[str, ChurnMetrics] = {}
    for module in sorted(module_data):
        bucket = module_data[module]
        total_churn = bucket["total_added"] + bucket["total_removed"]
        ai_churn = bucket["ai_added"] + bucket["ai_removed"]
        ai_pct = (ai_churn / total_churn * 100.0) if total_churn > 0 else 0.0

        result[module] = ChurnMetrics(
            total_churn_lines=total_churn,
            ai_churn_lines=ai_churn,
            ai_churn_attribution_pct=ai_pct,
        )

    return result
