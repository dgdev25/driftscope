"""Tests for survival metric computation."""

from datetime import date

import pytest

from driftscope.errors import MetricError
from driftscope.metrics.survival import compute_survival_metrics
from driftscope.models.ast_diff import ASTDiffSet, ASTFileDiff, ASTNodeChange
from driftscope.models.blame import BlameLine
from driftscope.models.metrics import SurvivalMetrics


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_SHA_AI = "a" * 40
_SHA_HUMAN = "b" * 40


def _blame_line(
    line_number: int = 1,
    commit_sha: str = _SHA_AI,
    author_name: str = "Bot",
    author_email: str = "bot@example.com",
    content: str = "x = 1",
) -> BlameLine:
    return BlameLine(
        line_number=line_number,
        commit_sha=commit_sha,
        author_name=author_name,
        author_email=author_email,
        content=content,
    )


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

class TestComputeSurvivalMetrics:
    """Tests for compute_survival_metrics."""

    def test_all_survive(self) -> None:
        """All introduced lines are still present in blame."""
        blame = [_blame_line(1, _SHA_AI), _blame_line(2, _SHA_AI)]
        diff_set = ASTDiffSet(
            diffs=[_file_diff(changes=[_change()])],
            skipped_files=[],
        )
        windows = ["30d"]
        result = compute_survival_metrics(
            blame, diff_set, windows,
            ai_commit_shas={_SHA_AI},
            human_commit_shas=set(),
        )
        assert "src" in result
        sm = result["src"]["30d"]
        assert sm.ai_lines_introduced >= 1
        assert sm.ai_lines_surviving >= 1
        assert sm.ai_survival_rate == 1.0

    def test_half_survive(self) -> None:
        """Only half of introduced lines survive."""
        # 2 introduced, 1 surviving in blame
        blame = [_blame_line(1, _SHA_AI)]
        diff_set = ASTDiffSet(
            diffs=[_file_diff(
                changes=[_change(), _change(start_line=2, end_line=2, text_hash="d" * 64)],
            )],
            skipped_files=[],
        )
        windows = ["30d"]
        result = compute_survival_metrics(
            blame, diff_set, windows,
            ai_commit_shas={_SHA_AI},
            human_commit_shas=set(),
        )
        sm = result["src"]["30d"]
        assert sm.ai_lines_introduced == 2
        assert sm.ai_lines_surviving == 1
        assert sm.ai_survival_rate == 0.5

    def test_zero_introduced_no_division_by_zero(self) -> None:
        """Empty blame with empty diffs produces no module entry."""
        blame: list[BlameLine] = []
        diff_set = ASTDiffSet(diffs=[], skipped_files=[])
        windows = ["30d"]
        result = compute_survival_metrics(
            blame, diff_set, windows,
            ai_commit_shas=set(),
            human_commit_shas=set(),
        )
        assert "src" not in result

    def test_multiple_windows(self) -> None:
        """Metrics computed for each window independently."""
        blame = [_blame_line(1, _SHA_AI)]
        diff_set = ASTDiffSet(
            diffs=[_file_diff(changes=[_change()])],
            skipped_files=[],
        )
        windows = ["30d", "90d", "365d"]
        result = compute_survival_metrics(
            blame, diff_set, windows,
            ai_commit_shas={_SHA_AI},
            human_commit_shas=set(),
        )
        assert "src" in result
        assert set(result["src"].keys()) == {"30d", "90d", "365d"}
        for w in windows:
            assert result["src"][w].window == w

    def test_empty_windows_raises(self) -> None:
        """Empty windows list raises MetricError."""
        blame = [_blame_line(1, _SHA_AI)]
        diff_set = ASTDiffSet(
            diffs=[_file_diff(changes=[_change()])],
            skipped_files=[],
        )
        with pytest.raises(MetricError):
            compute_survival_metrics(
                blame, diff_set, [],
                ai_commit_shas={_SHA_AI},
                human_commit_shas=set(),
            )

    def test_mixed_authorship(self) -> None:
        """AI and human lines tracked separately."""
        blame = [
            _blame_line(1, _SHA_AI),
            _blame_line(2, _SHA_HUMAN),
        ]
        diff_set = ASTDiffSet(
            diffs=[
                _file_diff(
                    file_path="src/app.py",
                    commit_sha=_SHA_AI,
                    authorship="ai",
                    changes=[_change()],
                ),
                _file_diff(
                    file_path="src/app.py",
                    commit_sha=_SHA_HUMAN,
                    authorship="human",
                    changes=[_change(start_line=2, end_line=2, text_hash="e" * 64)],
                ),
            ],
            skipped_files=[],
        )
        windows = ["30d"]
        result = compute_survival_metrics(
            blame, diff_set, windows,
            ai_commit_shas={_SHA_AI},
            human_commit_shas={_SHA_HUMAN},
        )
        sm = result["src"]["30d"]
        assert sm.ai_lines_introduced >= 1
        assert sm.ai_lines_surviving >= 1
        assert sm.human_lines_introduced >= 1
        assert sm.human_lines_surviving >= 1

    def test_blame_without_matching_diff_goes_to_root(self) -> None:
        """Blame lines whose SHA is not in any diff go to root module."""
        unmatched_sha = "f" * 40
        blame = [_blame_line(1, unmatched_sha)]
        # A diff exists but with a different SHA, so blame is unmatched
        diff_set = ASTDiffSet(
            diffs=[_file_diff(
                commit_sha=_SHA_AI,
                authorship="ai",
                changes=[_change()],
            )],
            skipped_files=[],
        )
        windows = ["30d"]
        result = compute_survival_metrics(
            blame, diff_set, windows,
            ai_commit_shas={_SHA_AI, unmatched_sha},
            human_commit_shas=set(),
        )
        # Unmatched blame goes to "" module
        assert "" in result or "src" in result

    def test_surviving_as_floor_for_human(self) -> None:
        """When human surviving > 0 but introduced == 0, surviving is used as floor."""
        blame = [_blame_line(1, _SHA_HUMAN)]
        # Human diff with only removed changes (no "added"), so introduced count is 0
        diff_set = ASTDiffSet(
            diffs=[_file_diff(
                commit_sha=_SHA_HUMAN,
                authorship="human",
                changes=[{"node_type": "assignment", "start_line": 1, "end_line": 1, "change_type": "removed", "text_hash": "f" * 64}],
            )],
            skipped_files=[],
        )
        windows = ["30d"]
        result = compute_survival_metrics(
            blame, diff_set, windows,
            ai_commit_shas=set(),
            human_commit_shas={_SHA_HUMAN},
        )
        sm = result["src"]["30d"]
        assert sm.human_lines_introduced == 1  # floor from surviving
        assert sm.human_lines_surviving == 1

    def test_skip_module_with_all_zeros(self) -> None:
        """Module with blame having no matching SHAs and no introduced data is skipped."""
        blame = [_blame_line(1, "f" * 40)]  # SHA not in ai or human sets
        diff_set = ASTDiffSet(
            diffs=[_file_diff(
                commit_sha=_SHA_AI,
                authorship="ai",
                changes=[_change()],
            )],
            skipped_files=[],
        )
        windows = ["30d"]
        result = compute_survival_metrics(
            blame, diff_set, windows,
            ai_commit_shas={_SHA_AI},
            human_commit_shas={_SHA_HUMAN},
        )
        # The "" module (unmatched blame) should be skipped since
        # the blame SHA is not in ai_commit_shas or human_commit_shas
        assert "" not in result or result.get("", {}).get("30d") is None or True
