"""CSV export renderer — one row per module per survival window.

Time Complexity: O(n * w) where n is the number of modules and w is the
average number of survival windows per module.
Space Complexity: O(n * w) for the output string.
"""

from __future__ import annotations

import csv
import io

from driftscope.models.report import MetricsResult

_HEADERS = [
    "module",
    "window",
    "ai_lines_introduced",
    "ai_lines_surviving",
    "ai_survival_rate",
    "human_lines_introduced",
    "human_lines_surviving",
    "human_survival_rate",
    "cyclomatic_delta_ai",
    "cyclomatic_delta_human",
    "cognitive_delta_ai",
    "cognitive_delta_human",
    "total_churn_lines",
    "ai_churn_attribution_pct",
]


def render_csv(result: MetricsResult) -> str:
    """Render a MetricsResult as CSV with one row per module per survival window.

    Each module contributes one row for every survival window in its
    ``result.survival`` dictionary. Complexity and churn values are repeated
    per row (they are module-level, not window-level).

    Args:
        result: The analysis result to export.

    Returns:
        A CSV string with a header row and 14 columns per data row.
    """
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(_HEADERS)

    for mod in result.modules:
        for window_key in sorted(mod.survival.keys()):
            sm = mod.survival[window_key]
            writer.writerow([
                mod.module_path,
                sm.window,
                sm.ai_lines_introduced,
                sm.ai_lines_surviving,
                sm.ai_survival_rate,
                sm.human_lines_introduced,
                sm.human_lines_surviving,
                sm.human_survival_rate,
                mod.complexity.cyclomatic_delta_ai,
                mod.complexity.cyclomatic_delta_human,
                mod.complexity.cognitive_delta_ai,
                mod.complexity.cognitive_delta_human,
                mod.churn.total_churn_lines,
                mod.churn.ai_churn_attribution_pct,
            ])

    return buf.getvalue()
