"""Line survival rate computation from AST diffs and git blame.

Counts lines introduced by AI vs. human commits and determines how
many survive within a given time window based on blame data.
"""

from __future__ import annotations

from driftscope.models.ast_diff import ASTDiffSet
from driftscope.models.blame import BlameLine
from driftscope.models.metrics import SurvivalMetrics


def compute_survival(
    diff_set: ASTDiffSet,
    blame: list[BlameLine],
    window: str,
    ai_commit_shas: set[str],
    human_commit_shas: set[str],
) -> SurvivalMetrics:
    """Compute line survival rates from AST diffs and blame data.

    Counts lines introduced (added nodes) by authorship class from the
    diff set, then counts surviving lines from blame where the commit SHA
    matches the AI or human commit sets.

    Args:
        diff_set: Collection of AST file diffs with node changes.
        blame: Current blame lines for the file(s).
        window: Time window string (e.g. ``"30d"``, ``"90d"``).
        ai_commit_shas: Set of 40-char hex SHAs attributed to AI.
        human_commit_shas: Set of 40-char hex SHAs attributed to humans.

    Returns:
        SurvivalMetrics with introduction counts, surviving counts,
        and survival rates for both AI and human contributions.

    Time Complexity: O(d * c + b) where d = number of diffs,
        c = changes per diff, b = number of blame lines.
    Space Complexity: O(1) additional beyond inputs.
    """
    ai_lines_introduced = 0
    human_lines_introduced = 0

    for file_diff in diff_set.diffs:
        for change in file_diff.changes:
            if change.change_type != "added":
                continue
            line_count = change.end_line - change.start_line + 1
            if file_diff.authorship_class == "ai":
                ai_lines_introduced += line_count
            else:
                human_lines_introduced += line_count

    ai_lines_surviving = 0
    human_lines_surviving = 0

    for blame_line in blame:
        if blame_line.commit_sha in ai_commit_shas:
            ai_lines_surviving += 1
        elif blame_line.commit_sha in human_commit_shas:
            human_lines_surviving += 1

    ai_survival_rate = (
        ai_lines_surviving / ai_lines_introduced
        if ai_lines_introduced > 0
        else 0.0
    )
    human_survival_rate = (
        human_lines_surviving / human_lines_introduced
        if human_lines_introduced > 0
        else 0.0
    )

    return SurvivalMetrics(
        window=window,
        ai_lines_introduced=ai_lines_introduced,
        ai_lines_surviving=ai_lines_surviving,
        ai_survival_rate=ai_survival_rate,
        human_lines_introduced=human_lines_introduced,
        human_lines_surviving=human_lines_surviving,
        human_survival_rate=human_survival_rate,
    )
