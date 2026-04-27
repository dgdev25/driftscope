"""Tests for driftscope.ast_engine.survival."""

import pytest

from driftscope.ast_engine.survival import compute_survival
from driftscope.ast_engine.parser import compute_text_hash
from driftscope.models.ast_diff import ASTDiffSet, ASTFileDiff, ASTNodeChange
from driftscope.models.blame import BlameLine
from driftscope.models.metrics import SurvivalMetrics


def _make_diff(
    authorship_class: str,
    changes: list[ASTNodeChange],
    commit_sha: str | None = None,
) -> ASTFileDiff:
    """Helper to build an ASTFileDiff for testing."""
    return ASTFileDiff(
        file_path="test.py",
        commit_sha=commit_sha or "a" * 40,
        before_hash=None,
        after_hash=None,
        changes=changes,
        authorship_class=authorship_class,
    )


def _make_change(
    change_type: str,
    start_line: int,
    end_line: int,
    node_type: str = "identifier",
) -> ASTNodeChange:
    """Helper to build an ASTNodeChange for testing."""
    return ASTNodeChange(
        node_type=node_type,
        start_line=start_line,
        end_line=end_line,
        change_type=change_type,
        text_hash=compute_text_hash(f"{node_type}:{start_line}:{end_line}"),
    )


def _make_blame(commit_sha: str, count: int, start: int = 1) -> list[BlameLine]:
    """Helper to build blame lines for testing."""
    return [
        BlameLine(
            line_number=i,
            commit_sha=commit_sha,
            author_name="Author",
            author_email="author@example.com",
            content=f"line {i}",
        )
        for i in range(start, start + count)
    ]


AI_SHA = "a" * 40
HUMAN_SHA = "b" * 40
OTHER_SHA = "c" * 40


class TestComputeSurvival:
    """Tests for compute_survival."""

    def test_ai_only_survival(self) -> None:
        """AI-introduced lines with matching blame produce correct rate."""
        diff_set = ASTDiffSet(
            diffs=[
                _make_diff("ai", [_make_change("added", 1, 10)], commit_sha=AI_SHA),
            ],
            skipped_files=[],
        )
        blame = _make_blame(AI_SHA, 10)

        result = compute_survival(
            diff_set=diff_set,
            blame=blame,
            window="30d",
            ai_commit_shas={AI_SHA},
            human_commit_shas={HUMAN_SHA},
        )
        assert isinstance(result, SurvivalMetrics)
        assert result.ai_lines_introduced == 10
        assert result.ai_lines_surviving == 10
        assert result.ai_survival_rate == 1.0
        assert result.human_lines_introduced == 0

    def test_human_only_survival(self) -> None:
        """Human-introduced lines with matching blame produce correct rate."""
        diff_set = ASTDiffSet(
            diffs=[
                _make_diff("human", [_make_change("added", 1, 5)], commit_sha=HUMAN_SHA),
            ],
            skipped_files=[],
        )
        blame = _make_blame(HUMAN_SHA, 3)

        result = compute_survival(
            diff_set=diff_set,
            blame=blame,
            window="90d",
            ai_commit_shas={AI_SHA},
            human_commit_shas={HUMAN_SHA},
        )
        assert result.human_lines_introduced == 5
        assert result.human_lines_surviving == 3
        assert result.human_survival_rate == pytest.approx(3 / 5)

    def test_mixed_authorship(self) -> None:
        """Both AI and human contributions are tracked independently."""
        diff_set = ASTDiffSet(
            diffs=[
                _make_diff("ai", [_make_change("added", 1, 4)], commit_sha=AI_SHA),
                _make_diff("human", [_make_change("added", 5, 9)], commit_sha=HUMAN_SHA),
            ],
            skipped_files=[],
        )
        blame = _make_blame(AI_SHA, 4) + _make_blame(HUMAN_SHA, 3, start=5)

        result = compute_survival(
            diff_set=diff_set,
            blame=blame,
            window="180d",
            ai_commit_shas={AI_SHA},
            human_commit_shas={HUMAN_SHA},
        )
        assert result.ai_lines_introduced == 4
        assert result.human_lines_introduced == 5
        assert result.ai_lines_surviving == 4
        assert result.human_lines_surviving == 3

    def test_zero_introduced_gives_zero_rate(self) -> None:
        """No introduced lines must yield survival rate 0.0."""
        diff_set = ASTDiffSet(diffs=[], skipped_files=[])
        blame: list[BlameLine] = []

        result = compute_survival(
            diff_set=diff_set,
            blame=blame,
            window="365d",
            ai_commit_shas=set(),
            human_commit_shas=set(),
        )
        assert result.ai_survival_rate == 0.0
        assert result.human_survival_rate == 0.0
        assert result.ai_lines_introduced == 0
        assert result.human_lines_introduced == 0

    def test_removed_changes_are_ignored(self) -> None:
        """Only 'added' changes count toward lines introduced."""
        diff_set = ASTDiffSet(
            diffs=[
                _make_diff(
                    "ai",
                    [
                        _make_change("removed", 1, 5),
                        _make_change("added", 6, 10),
                    ],
                    commit_sha=AI_SHA,
                ),
            ],
            skipped_files=[],
        )
        blame = _make_blame(AI_SHA, 5, start=6)

        result = compute_survival(
            diff_set=diff_set,
            blame=blame,
            window="30d",
            ai_commit_shas={AI_SHA},
            human_commit_shas={HUMAN_SHA},
        )
        # Only the "added" change (lines 6-10 = 5 lines) should count
        assert result.ai_lines_introduced == 5
