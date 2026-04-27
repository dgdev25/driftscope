"""Tests for commit classification."""

from datetime import datetime, timezone
from pathlib import Path

import pytest

from driftscope.authorship.classifier import classify_commit, classify_history
from driftscope.authorship.patterns import compile_patterns
from driftscope.models.blame import BlameLine
from driftscope.models.commit import Commit
from driftscope.models.history import CommitHistory


def _commit(message_subject: str = "Update code", message_body: str = "") -> Commit:
    return Commit(
        sha="a" * 40,
        short_sha="a" * 7,
        timestamp=datetime(2025, 6, 15, 10, 0, tzinfo=timezone.utc),
        author_name="Alice",
        author_email="alice@example.com",
        committer_name="Alice",
        committer_email="alice@example.com",
        message_subject=message_subject,
        message_body=message_body,
        parent_shas=["b" * 40],
    )


class TestClassifyCommit:
    def test_copilot_tag_classified_as_ai(self) -> None:
        commit = _commit(
            message_subject="Add payment handler",
            message_body="Co-Authored-By: GitHub Copilot\n",
        )
        patterns = compile_patterns()
        result = classify_commit(commit, patterns)
        assert result.authorship_class == "ai"
        assert result.matched_pattern == "github_copilot"
        assert "Copilot" in result.matched_text

    def test_claude_tag_classified_as_ai(self) -> None:
        commit = _commit(message_body="Co-Authored-By: Claude\n")
        patterns = compile_patterns()
        result = classify_commit(commit, patterns)
        assert result.authorship_class == "ai"
        assert result.matched_pattern == "claude_code"

    def test_no_tag_classified_as_human(self) -> None:
        commit = _commit(message_subject="Fix typo")
        patterns = compile_patterns()
        result = classify_commit(commit, patterns)
        assert result.authorship_class == "human"
        assert result.matched_pattern is None
        assert result.matched_text is None

    def test_custom_pattern_match(self) -> None:
        commit = _commit(message_body="MyBot: auto-generated\n")
        patterns = compile_patterns(custom_patterns=[r"MyBot:\s*auto-generated"])
        result = classify_commit(commit, patterns)
        assert result.authorship_class == "ai"
        assert "MyBot" in result.matched_text

    def test_builtin_disabled_no_match(self) -> None:
        commit = _commit(message_body="Co-Authored-By: GitHub Copilot\n")
        patterns = compile_patterns(include_builtins=False)
        result = classify_commit(commit, patterns)
        assert result.authorship_class == "human"

    def test_ai_generated_trailer_match(self) -> None:
        commit = _commit(message_body="AI-Generated: payment validation logic\n")
        patterns = compile_patterns()
        result = classify_commit(commit, patterns)
        assert result.authorship_class == "ai"

    def test_multiline_body_match(self) -> None:
        commit = _commit(
            message_body="Implement feature\n\nDetails here.\n\nCo-Authored-By: Cursor\n",
        )
        patterns = compile_patterns()
        result = classify_commit(commit, patterns)
        assert result.authorship_class == "ai"

    def test_empty_message_body(self) -> None:
        commit = _commit(message_body="")
        patterns = compile_patterns()
        result = classify_commit(commit, patterns)
        assert result.authorship_class == "human"

    def test_unicode_in_message(self) -> None:
        commit = _commit(message_body="Fix Übersicht\n")
        patterns = compile_patterns()
        result = classify_commit(commit, patterns)
        assert result.authorship_class == "human"


class TestClassifyHistory:
    def test_mixed_history_counts(self) -> None:
        history = CommitHistory(
            repo_path=Path("/tmp/repo"),
            commits=[
                _commit(message_body="Co-Authored-By: Claude\n"),
                _commit(message_subject="Human commit"),
                _commit(message_body="Co-Authored-By: GitHub Copilot\n"),
            ],
            blame={},
            range_start=datetime(2025, 1, 1, tzinfo=timezone.utc),
            range_end=datetime(2025, 6, 1, tzinfo=timezone.utc),
        )
        result = classify_history(history)
        assert result.ai_commit_count == 2
        assert result.human_commit_count == 1
        assert len(result.commits) == 3

    def test_all_human_history(self) -> None:
        history = CommitHistory(
            repo_path=Path("/tmp/repo"),
            commits=[_commit(), _commit()],
            blame={},
            range_start=datetime(2025, 1, 1, tzinfo=timezone.utc),
            range_end=datetime(2025, 6, 1, tzinfo=timezone.utc),
        )
        result = classify_history(history)
        assert result.ai_commit_count == 0
        assert result.human_commit_count == 2

    def test_empty_history(self) -> None:
        history = CommitHistory(
            repo_path=Path("/tmp/repo"),
            commits=[],
            blame={},
            range_start=datetime(2025, 1, 1, tzinfo=timezone.utc),
            range_end=datetime(2025, 6, 1, tzinfo=timezone.utc),
        )
        result = classify_history(history)
        assert result.ai_commit_count == 0
        assert result.human_commit_count == 0

    def test_blame_data_preserved(self) -> None:
        blame = {Path("src/main.py"): [BlameLine(
            line_number=1,
            commit_sha="a" * 40,
            author_name="Alice",
            author_email="alice@example.com",
            content="x = 1",
        )]}
        history = CommitHistory(
            repo_path=Path("/tmp/repo"),
            commits=[_commit()],
            blame=blame,
            range_start=datetime(2025, 1, 1, tzinfo=timezone.utc),
            range_end=datetime(2025, 6, 1, tzinfo=timezone.utc),
        )
        result = classify_history(history)
        assert Path("src/main.py") in result.blame
