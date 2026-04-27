"""Tests for complexity metric computation."""

from datetime import date
from pathlib import Path

import pytest

from driftscope.metrics.complexity import (
    _build_weekly_series,
    compute_complexity_metrics,
    count_cognitive,
    count_cyclomatic,
)
from driftscope.models.ast_diff import ASTDiffSet, ASTFileDiff, ASTNodeChange


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _file_diff(
    file_path: str = "src/app.py",
    commit_sha: str = "a" * 40,
    authorship: str = "ai",
    changes: list[dict] | None = None,
    commit_date: date | None = None,
) -> ASTFileDiff:
    """Create an ASTFileDiff for testing."""
    node_changes = []
    for c in (changes or [{"node_type": "function_definition", "start_line": 1, "end_line": 1, "change_type": "added", "text_hash": "b" * 64}]):
        node_changes.append(ASTNodeChange(**c))
    d = ASTFileDiff(
        file_path=Path(file_path),
        commit_sha=commit_sha,
        changes=node_changes,
        authorship_class=authorship,
    )
    # Attach optional commit_date via model_extra — but ASTFileDiff is not frozen,
    # so we store it as a private attribute the caller can use for commit_weeks.
    return d


# ---------------------------------------------------------------------------
# TestCountCyclomatic
# ---------------------------------------------------------------------------

class TestCountCyclomatic:
    """Tests for count_cyclomatic heuristic."""

    def test_empty_source(self) -> None:
        assert count_cyclomatic("") == 0

    def test_no_decision_points(self) -> None:
        source = "x = 1\ny = 2\nreturn x + y\n"
        assert count_cyclomatic(source) == 0

    def test_if_statement(self) -> None:
        assert count_cyclomatic("if x:\n    pass\n") == 1

    def test_elif_counts(self) -> None:
        source = "if a:\n    pass\nelif b:\n    pass\n"
        assert count_cyclomatic(source) == 2

    def test_for_loop(self) -> None:
        assert count_cyclomatic("for i in range(n):\n    pass\n") == 1

    def test_while_loop(self) -> None:
        assert count_cyclomatic("while True:\n    break\n") == 1

    def test_boolean_operators(self) -> None:
        source = "if a and b or c:\n    pass\n"
        count = count_cyclomatic(source)
        # "and" and "or" each count as +1 decision point
        assert count >= 2

    def test_except_handler(self) -> None:
        source = "try:\n    pass\nexcept Exception:\n    pass\n"
        assert count_cyclomatic(source) >= 1

    def test_ternary_expression(self) -> None:
        source = "x = 1 if True else 2\n"
        # ternary "if" pattern should be counted
        assert count_cyclomatic(source) >= 1


# ---------------------------------------------------------------------------
# TestCountCognitive
# ---------------------------------------------------------------------------

class TestCountCognitive:
    """Tests for count_cognitive heuristic."""

    def test_flat_code_equals_cyclomatic(self) -> None:
        source = "if x:\n    pass\n"
        assert count_cognitive(source) == count_cyclomatic(source)

    def test_nested_increments(self) -> None:
        source = "if a:\n    if b:\n        pass\n"
        # The inner "if" is at nesting depth 1, so cognitive > cyclomatic
        cognitive = count_cognitive(source)
        cyclomatic = count_cyclomatic(source)
        assert cognitive > cyclomatic

    def test_empty_lines_ignored(self) -> None:
        """Empty lines should not affect cognitive complexity."""
        source = "if a:\n\n\n    pass\n"
        cognitive = count_cognitive(source)
        assert cognitive >= 1


# ---------------------------------------------------------------------------
# TestComputeComplexityMetrics
# ---------------------------------------------------------------------------

class TestComputeComplexityMetrics:
    """Tests for compute_complexity_metrics."""

    def test_empty_diff_set(self) -> None:
        diff_set = ASTDiffSet(diffs=[], skipped_files=[])
        result = compute_complexity_metrics(diff_set, {})
        assert result == {}

    def test_single_ai_diff(self) -> None:
        changes = [
            {
                "node_type": "function_definition",
                "start_line": 1,
                "end_line": 5,
                "change_type": "added",
                "text_hash": "c" * 64,
            },
        ]
        diff = _file_diff(
            file_path="src/app.py",
            commit_sha="a" * 40,
            authorship="ai",
            changes=changes,
        )
        diff_set = ASTDiffSet(diffs=[diff], skipped_files=[])
        # commit_weeks maps commit_sha -> iso week start date
        commit_weeks = {"a" * 40: date(2025, 1, 6)}
        result = compute_complexity_metrics(diff_set, commit_weeks)
        assert "src" in result
        m = result["src"]
        assert m.cyclomatic_delta_ai >= 0
        assert m.cyclomatic_delta_human == 0.0
        assert len(m.weekly_series) >= 1

    def test_mixed_authorship(self) -> None:
        ai_changes = [
            {"node_type": "if_statement", "start_line": 1, "end_line": 2, "change_type": "added", "text_hash": "d" * 64},
        ]
        human_changes = [
            {"node_type": "for_statement", "start_line": 3, "end_line": 4, "change_type": "added", "text_hash": "e" * 64},
        ]
        ai_diff = _file_diff(
            file_path="src/mod.py",
            commit_sha="a" * 40,
            authorship="ai",
            changes=ai_changes,
        )
        human_diff = _file_diff(
            file_path="src/mod.py",
            commit_sha="b" * 40,
            authorship="human",
            changes=human_changes,
        )
        diff_set = ASTDiffSet(diffs=[ai_diff, human_diff], skipped_files=[])
        commit_weeks = {
            "a" * 40: date(2025, 1, 6),
            "b" * 40: date(2025, 1, 13),
        }
        result = compute_complexity_metrics(diff_set, commit_weeks)
        assert "src" in result
        m = result["src"]
        assert m.cyclomatic_delta_ai > 0
        assert m.cyclomatic_delta_human > 0
