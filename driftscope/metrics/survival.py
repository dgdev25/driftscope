"""Survival metric computation — line survival rates per time window.

Computes what fraction of introduced lines (segmented by AI vs. human
authorship) are still present in the current blame snapshot.

Time Complexity:
    - compute_survival_metrics: O(B + D) where B = blame lines, D = diffs
"""

from __future__ import annotations

from collections import defaultdict

from driftscope.errors import MetricError
from driftscope.metrics._helpers import module_of
from driftscope.models.ast_diff import ASTDiffSet
from driftscope.models.blame import BlameLine
from driftscope.models.metrics import SurvivalMetrics


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def compute_survival_metrics(
    blame: list[BlameLine],
    diff_set: ASTDiffSet,
    windows: list[str],
    ai_commit_shas: set[str],
    human_commit_shas: set[str],
) -> dict[str, dict[str, SurvivalMetrics]]:
    """Compute line survival rates per module per time window.

    For each module and each time window, counts how many lines were
    introduced (from diffs) and how many are still surviving (from blame),
    segmented by AI and human authorship.

    Args:
        blame: Current blame snapshot lines for the repository.
        diff_set: AST diffs providing introduction events.
        windows: List of window strings (e.g. ["30d", "90d", "365d"]).
            Must be non-empty or MetricError is raised.
        ai_commit_shas: Set of commit SHAs attributed to AI authorship.
        human_commit_shas: Set of commit SHAs attributed to human authorship.

    Returns:
        Nested dict: module -> window -> SurvivalMetrics.

    Raises:
        MetricError: If *windows* is empty.

    Time Complexity: O(B + D) where B = blame lines, D = diffs.
    """
    if not windows:
        raise MetricError("windows list must not be empty")

    # Build commit_sha -> set of modules mapping from diffs
    sha_modules: dict[str, set[str]] = defaultdict(set)
    for diff in diff_set.diffs:
        sha_modules[diff.commit_sha].add(module_of(diff.file_path))

    # Group blame lines by module using sha_modules mapping.
    # A blame line belongs to a module if its commit SHA was used in a diff
    # for that module.  Unmatched blame lines go to "" (root).
    blame_by_module: dict[str, list[BlameLine]] = defaultdict(list)
    for bl in blame:
        modules = sha_modules.get(bl.commit_sha)
        if modules:
            for mod in modules:
                blame_by_module[mod].append(bl)
        else:
            blame_by_module[""].append(bl)

    # Count introduced lines by module and authorship
    introduced_by_module = _count_introduced_by_module(diff_set)

    # Collect all modules from both sources
    all_modules = set(blame_by_module.keys()) | set(introduced_by_module.keys())
    if not all_modules:
        return {}

    result: dict[str, dict[str, SurvivalMetrics]] = {}

    for module in sorted(all_modules):
        module_blame = blame_by_module.get(module, [])
        module_introduced = introduced_by_module.get(module, {"ai": 0, "human": 0})

        # Count surviving lines from blame
        ai_surviving = sum(1 for bl in module_blame if bl.commit_sha in ai_commit_shas)
        human_surviving = sum(1 for bl in module_blame if bl.commit_sha in human_commit_shas)

        ai_introduced = module_introduced["ai"]
        human_introduced = module_introduced["human"]

        # If no introduced data from diffs but surviving > 0,
        # use surviving as floor for introduced
        if ai_introduced == 0 and ai_surviving > 0:
            ai_introduced = ai_surviving
        if human_introduced == 0 and human_surviving > 0:
            human_introduced = human_surviving

        # Skip modules with no data
        if ai_introduced == 0 and human_introduced == 0 and ai_surviving == 0 and human_surviving == 0:
            continue

        result[module] = {}
        for window in windows:
            ai_rate = ai_surviving / ai_introduced if ai_introduced > 0 else 0.0
            human_rate = human_surviving / human_introduced if human_introduced > 0 else 0.0

            # Clamp rates to [0.0, 1.0]
            ai_rate = min(max(ai_rate, 0.0), 1.0)
            human_rate = min(max(human_rate, 0.0), 1.0)

            result[module][window] = SurvivalMetrics(
                window=window,
                ai_lines_introduced=ai_introduced,
                ai_lines_surviving=ai_surviving,
                ai_survival_rate=ai_rate,
                human_lines_introduced=human_introduced,
                human_lines_surviving=human_surviving,
                human_survival_rate=human_rate,
            )

    return result


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _count_introduced_by_module(
    diff_set: ASTDiffSet,
) -> dict[str, dict[str, int]]:
    """Count introduced ("added") changes by authorship per module.

    Args:
        diff_set: Collection of AST file diffs.

    Returns:
        Dict mapping module name to {"ai": count, "human": count}.

    Time Complexity: O(D * C) where D = diffs, C = changes per diff.
    """
    result: dict[str, dict[str, int]] = defaultdict(lambda: {"ai": 0, "human": 0})
    for diff in diff_set.diffs:
        mod = module_of(diff.file_path)
        added_count = sum(1 for ch in diff.changes if ch.change_type == "added")
        if diff.authorship_class == "ai":
            result[mod]["ai"] += added_count
        else:
            result[mod]["human"] += added_count
    return dict(result)
