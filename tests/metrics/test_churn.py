"""Tests for churn metric computation."""

import pytest

from driftscope.metrics.churn import compute_churn_metrics
from driftscope.models.ast_diff import ASTDiffSet, ASTFileDiff, ASTNodeChange


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_SHA_AI = "a" * 40
_SHA_HUMAN = "b" * 40


def _change(
    node_type: str = "assignment",
    start_line: int = 1,
    end_line: int = 1,
    change_type: str = "added",
    text_hash: str = "c" * 64,
) -> dict:
    return {
        "node_type": node_type,
        "start_line": start_line,
        "end_line": end_line,
        "change_type": change_type,
        "text_hash": text_hash,
    }


def _file_diff(
    file_path: str = "src/app.py",
    commit_sha: str = _SHA_AI,
    authorship: str = "ai",
    changes: list[dict] | None = None,
) -> ASTFileDiff:
    node_changes = [ASTNodeChange(**c) for c in (changes or [_change()])]
    return ASTFileDiff(
        file_path=file_path,  # type: ignore[arg-type]
        commit_sha=commit_sha,
        changes=node_changes,
        authorship_class=authorship,  # type: ignore[arg-type]
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestComputeChurnMetrics:
    """Tests for compute_churn_metrics."""

    def test_empty_diff_set(self) -> None:
        """Empty diffs produce empty result."""
        diff_set = ASTDiffSet(diffs=[], skipped_files=[])
        result = compute_churn_metrics(diff_set)
        assert result == {}

    def test_all_ai(self) -> None:
        """All changes from AI authorship."""
        diff_set = ASTDiffSet(
            diffs=[_file_diff(
                authorship="ai",
                changes=[
                    _change(change_type="added"),
                    _change(change_type="removed", text_hash="d" * 64),
                ],
            )],
            skipped_files=[],
        )
        result = compute_churn_metrics(diff_set)
        assert "src" in result
        m = result["src"]
        assert m.ai_churn_lines == 2  # 1 added + 1 removed
        assert m.total_churn_lines == 2
        assert m.ai_churn_attribution_pct == 100.0

    def test_all_human(self) -> None:
        """All changes from human authorship."""
        diff_set = ASTDiffSet(
            diffs=[_file_diff(
                authorship="human",
                changes=[
                    _change(change_type="added"),
                    _change(change_type="removed", text_hash="d" * 64),
                ],
            )],
            skipped_files=[],
        )
        result = compute_churn_metrics(diff_set)
        assert "src" in result
        m = result["src"]
        assert m.ai_churn_lines == 0
        assert m.total_churn_lines == 2
        assert m.ai_churn_attribution_pct == 0.0

    def test_mixed_authorship(self) -> None:
        """Mixed AI and human changes."""
        diff_set = ASTDiffSet(
            diffs=[
                _file_diff(
                    authorship="ai",
                    changes=[_change(change_type="added")],
                ),
                _file_diff(
                    file_path="src/app.py",
                    commit_sha=_SHA_HUMAN,
                    authorship="human",
                    changes=[
                        _change(change_type="added", text_hash="d" * 64),
                        _change(change_type="removed", text_hash="e" * 64),
                    ],
                ),
            ],
            skipped_files=[],
        )
        result = compute_churn_metrics(diff_set)
        m = result["src"]
        assert m.total_churn_lines == 3  # 1 ai-added + 1 human-added + 1 human-removed
        assert m.ai_churn_lines == 1
        assert m.ai_churn_attribution_pct == pytest.approx(100.0 / 3.0)

    def test_no_changes(self) -> None:
        """Diffs with zero changes produce module with zero churn."""
        diff_set = ASTDiffSet(
            diffs=[ASTFileDiff(
                file_path="src/app.py",  # type: ignore[arg-type]
                commit_sha=_SHA_AI,
                changes=[],
                authorship_class="ai",  # type: ignore[arg-type]
            )],
            skipped_files=[],
        )
        result = compute_churn_metrics(diff_set)
        assert "src" in result
        m = result["src"]
        assert m.total_churn_lines == 0
        assert m.ai_churn_lines == 0
        assert m.ai_churn_attribution_pct == 0.0

    def test_multiple_modules(self) -> None:
        """Diffs across different modules produce separate entries."""
        diff_set = ASTDiffSet(
            diffs=[
                _file_diff(
                    file_path="src/app.py",
                    authorship="ai",
                    changes=[_change(change_type="added")],
                ),
                _file_diff(
                    file_path="lib/util.py",
                    authorship="human",
                    changes=[
                        _change(change_type="added", text_hash="d" * 64),
                        _change(change_type="removed", text_hash="e" * 64),
                    ],
                ),
            ],
            skipped_files=[],
        )
        result = compute_churn_metrics(diff_set)
        assert "src" in result
        assert "lib" in result
        assert result["src"].ai_churn_lines == 1
        assert result["src"].total_churn_lines == 1
        assert result["lib"].ai_churn_lines == 0
        assert result["lib"].total_churn_lines == 2
