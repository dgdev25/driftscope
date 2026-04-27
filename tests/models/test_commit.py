"""Tests for the Commit model."""

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from driftscope.models.commit import Commit


def _valid_commit(**overrides: object) -> dict:
    base = {
        "sha": "a" * 40,
        "short_sha": "a" * 7,
        "timestamp": datetime(2025, 1, 15, 10, 30, 0, tzinfo=timezone.utc),
        "author_name": "Alice",
        "author_email": "alice@example.com",
        "committer_name": "Alice",
        "committer_email": "alice@example.com",
        "message_subject": "Add feature",
        "message_body": "",
        "parent_shas": ["b" * 40],
    }
    base.update(overrides)
    return base


def test_commit_valid() -> None:
    commit = Commit(**_valid_commit())
    assert commit.sha == "a" * 40
    assert commit.short_sha == "a" * 7
    assert commit.parent_shas == ["b" * 40]


def test_commit_rejects_short_sha() -> None:
    with pytest.raises(ValidationError):
        Commit(**_valid_commit(short_sha="abc"))


def test_commit_rejects_non_hex_sha() -> None:
    with pytest.raises(ValidationError):
        Commit(**_valid_commit(sha="g" * 40))


def test_commit_rejects_sha_too_short() -> None:
    with pytest.raises(ValidationError):
        Commit(**_valid_commit(sha="a" * 39))


def test_commit_frozen() -> None:
    commit = Commit(**_valid_commit())
    with pytest.raises(ValidationError):
        commit.sha = "c" * 40  # type: ignore[misc]


def test_commit_merge_has_multiple_parents() -> None:
    commit = Commit(**_valid_commit(parent_shas=["b" * 40, "c" * 40]))
    assert len(commit.parent_shas) == 2
