"""Tests for the BlameLine model."""

import pytest
from pydantic import ValidationError

from driftscope.models.blame import BlameLine


def test_blame_line_valid() -> None:
    line = BlameLine(
        line_number=1,
        commit_sha="a" * 40,
        author_name="Alice",
        author_email="alice@example.com",
        content="x = 1",
    )
    assert line.line_number == 1
    assert line.content == "x = 1"


def test_blame_line_rejects_line_zero() -> None:
    with pytest.raises(ValidationError):
        BlameLine(
            line_number=0,
            commit_sha="a" * 40,
            author_name="Alice",
            author_email="alice@example.com",
            content="x = 1",
        )


def test_blame_line_rejects_invalid_sha() -> None:
    with pytest.raises(ValidationError):
        BlameLine(
            line_number=1,
            commit_sha="not-a-sha",
            author_name="Alice",
            author_email="alice@example.com",
            content="x = 1",
        )
