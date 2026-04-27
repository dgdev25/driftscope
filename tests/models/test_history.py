"""Tests for CommitHistory, AttributedCommit, and AttributedHistory models."""

from datetime import datetime, timezone
from pathlib import Path

import pytest
from pydantic import ValidationError

from driftscope.models.blame import BlameLine
from driftscope.models.commit import Commit
from driftscope.models.history import AttributedCommit, AttributedHistory, CommitHistory


def _commit(sha_suffix: str = "a") -> dict:
    return {
        "sha": sha_suffix * 40,
        "short_sha": sha_suffix * 7,
        "timestamp": datetime(2025, 1, 15, 10, 0, tzinfo=timezone.utc),
        "author_name": "Alice",
        "author_email": "alice@example.com",
        "committer_name": "Alice",
        "committer_email": "alice@example.com",
        "message_subject": "Commit",
        "message_body": "",
        "parent_shas": ["b" * 40],
    }


def test_commit_history_valid() -> None:
    history = CommitHistory(
        repo_path=Path("/tmp/repo"),
        commits=[Commit(**_commit("a")), Commit(**_commit("c"))],
        blame={Path("src/main.py"): [BlameLine(
            line_number=1,
            commit_sha="a" * 40,
            author_name="Alice",
            author_email="alice@example.com",
            content="print('hello')",
        )]},
        range_start=datetime(2025, 1, 1, tzinfo=timezone.utc),
        range_end=datetime(2025, 2, 1, tzinfo=timezone.utc),
    )
    assert len(history.commits) == 2
    assert history.repo_path == Path("/tmp/repo")
    assert Path("src/main.py") in history.blame


def test_attributed_commit_human() -> None:
    attr = AttributedCommit(**_commit(), authorship_class="human")
    assert attr.authorship_class == "human"
    assert attr.matched_pattern is None


def test_attributed_commit_ai() -> None:
    attr = AttributedCommit(
        **_commit(),
        authorship_class="ai",
        matched_pattern=r"Co-Authored-By:.*Copilot",
        matched_text="Co-Authored-By: GitHub Copilot",
    )
    assert attr.authorship_class == "ai"
    assert attr.matched_text == "Co-Authored-By: GitHub Copilot"


def test_attributed_history_counts() -> None:
    history = AttributedHistory(
        repo_path=Path("/tmp/repo"),
        commits=[
            AttributedCommit(**_commit("a"), authorship_class="ai", matched_pattern="p"),
            AttributedCommit(**_commit("c"), authorship_class="human"),
        ],
        blame={},
        range_start=datetime(2025, 1, 1, tzinfo=timezone.utc),
        range_end=datetime(2025, 2, 1, tzinfo=timezone.utc),
        ai_commit_count=1,
        human_commit_count=1,
    )
    assert history.ai_commit_count == 1
    assert history.human_commit_count == 1


def test_attributed_history_rejects_negative_counts() -> None:
    with pytest.raises(ValidationError):
        AttributedHistory(
            repo_path=Path("/tmp/repo"),
            commits=[],
            blame={},
            range_start=datetime(2025, 1, 1, tzinfo=timezone.utc),
            range_end=datetime(2025, 2, 1, tzinfo=timezone.utc),
            ai_commit_count=-1,
            human_commit_count=0,
        )
