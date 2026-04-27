"""Tests for driftscope.git_client.log."""

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from driftscope.errors import GitError
from driftscope.git_client.log import _parse_log_output, is_bare_repo, parse_log
from driftscope.models.commit import Commit


def _make_log_output(
    sha: str = "a" * 40,
    short_sha: str = "a" * 7,
    timestamp: str = "2024-01-15T10:30:00+00:00",
    author_name: str = "Alice",
    author_email: str = "alice@example.com",
    committer_name: str = "Alice",
    committer_email: str = "alice@example.com",
    subject: str = "Initial commit",
    body: str = "",
) -> str:
    """Build a single log record in the null-delimited format."""
    return f"{sha}\n{short_sha}\n{timestamp}\n{author_name}\n{author_email}\n{committer_name}\n{committer_email}\n{subject}\n{body}\x00"


class TestParseLogOutput:
    """Unit tests for _parse_log_output."""

    def test_single_commit(self) -> None:
        output = _make_log_output()
        commits = _parse_log_output(output)
        assert len(commits) == 1
        assert commits[0].sha == "a" * 40
        assert commits[0].short_sha == "a" * 7
        assert commits[0].message_subject == "Initial commit"

    def test_multiple_commits_oldest_first(self) -> None:
        output = (
            _make_log_output(sha="b" * 40, short_sha="b" * 7, timestamp="2024-01-20T10:00:00+00:00", subject="second")
            + _make_log_output(sha="a" * 40, short_sha="a" * 7, timestamp="2024-01-10T10:00:00+00:00", subject="first")
        )
        commits = _parse_log_output(output)
        assert len(commits) == 2
        # Reversed: oldest first
        assert commits[0].message_subject == "first"
        assert commits[1].message_subject == "second"

    def test_empty_output(self) -> None:
        assert _parse_log_output("") == []
        assert _parse_log_output("  \n  \n") == []

    def test_commit_with_body(self) -> None:
        output = _make_log_output(subject="feat: add login", body="This adds OAuth2 support.\n\nCo-authored-by: bot")
        commits = _parse_log_output(output)
        assert len(commits) == 1
        assert "OAuth2" in commits[0].message_body
        assert "Co-authored-by" in commits[0].message_body

    def test_malformed_record_skipped(self) -> None:
        """Records with too few fields are silently skipped."""
        output = "partial\ndata\n\x00" + _make_log_output()
        commits = _parse_log_output(output)
        assert len(commits) == 1

    def test_invalid_timestamp_skipped(self) -> None:
        output = _make_log_output(timestamp="not-a-date")
        commits = _parse_log_output(output)
        assert len(commits) == 0


class TestParseLog:
    """Tests for parse_log with mocked subprocess."""

    def test_parse_log_basic(self) -> None:
        log_output = _make_log_output(subject="test commit")
        mock_result = MagicMock()
        mock_result.stdout = log_output

        with patch("driftscope.git_client.log.subprocess.run", return_value=mock_result):
            commits = parse_log(Path("/repo"))

        assert len(commits) == 1
        assert commits[0].message_subject == "test commit"

    def test_parse_log_with_since(self) -> None:
        log_output = _make_log_output()
        mock_result = MagicMock()
        mock_result.stdout = log_output

        with patch("driftscope.git_client.log.subprocess.run", return_value=mock_result) as mock_run:
            parse_log(Path("/repo"), since="2024-01-01")

        cmd = mock_run.call_args[0][0]
        assert "--since=2024-01-01" in cmd

    def test_parse_log_with_ref_range(self) -> None:
        log_output = _make_log_output()
        mock_result = MagicMock()
        mock_result.stdout = log_output

        with patch("driftscope.git_client.log.subprocess.run", return_value=mock_result) as mock_run:
            parse_log(Path("/repo"), from_ref="main", to_ref="feature")

        cmd = mock_run.call_args[0][0]
        assert "main..feature" in cmd

    def test_parse_log_git_not_found(self) -> None:
        with patch("driftscope.git_client.log.subprocess.run", side_effect=FileNotFoundError):
            with pytest.raises(GitError, match="git binary not found"):
                parse_log(Path("/repo"))

    def test_parse_log_timeout(self) -> None:
        with patch(
            "driftscope.git_client.log.subprocess.run",
            side_effect=subprocess.TimeoutExpired(cmd="git", timeout=120),
        ):
            with pytest.raises(GitError, match="timed out"):
                parse_log(Path("/repo"))


class TestIsBareRepo:
    """Tests for is_bare_repo."""

    def test_bare_repo(self) -> None:
        mock_result = MagicMock()
        mock_result.stdout = "true\n"

        with patch("driftscope.git_client.log.subprocess.run", return_value=mock_result):
            assert is_bare_repo(Path("/repo")) is True

    def test_non_bare_repo(self) -> None:
        mock_result = MagicMock()
        mock_result.stdout = "false\n"

        with patch("driftscope.git_client.log.subprocess.run", return_value=mock_result):
            assert is_bare_repo(Path("/repo")) is False

    def test_bare_repo_git_not_found(self) -> None:
        with patch("driftscope.git_client.log.subprocess.run", side_effect=FileNotFoundError):
            with pytest.raises(GitError, match="git binary not found"):
                is_bare_repo(Path("/repo"))

    def test_bare_repo_timeout(self) -> None:
        with patch(
            "driftscope.git_client.log.subprocess.run",
            side_effect=subprocess.TimeoutExpired(cmd="git", timeout=10),
        ):
            with pytest.raises(GitError, match="timed out"):
                is_bare_repo(Path("/repo"))


class TestParseLogExtraCoverage:
    """Additional tests to close coverage gaps."""

    def test_parse_log_with_to_ref_only(self) -> None:
        """to_ref without from_ref appends to_ref directly."""
        mock_result = MagicMock()
        mock_result.stdout = _make_log_output()

        with patch("driftscope.git_client.log.subprocess.run", return_value=mock_result) as mock_run:
            parse_log(Path("/repo"), to_ref="HEAD")

        cmd = mock_run.call_args[0][0]
        assert cmd[-1] == "HEAD"

    def test_parse_log_called_process_error(self) -> None:
        """CalledProcessError is wrapped in GitError."""
        with patch(
            "driftscope.git_client.log.subprocess.run",
            side_effect=subprocess.CalledProcessError(
                returncode=128, cmd="git log", stderr="fatal: bad revision",
            ),
        ):
            with pytest.raises(GitError, match="git log failed"):
                parse_log(Path("/repo"))

    def test_parse_log_output_with_parent_in_body(self) -> None:
        """Parent SHAs are extracted from body lines."""
        output = _make_log_output(
            body="parent " + "a" * 40 + "\nsome other text",
        )
        commits = _parse_log_output(output)
        assert len(commits) == 1
        assert commits[0].parent_shas == ["a" * 40]

    def test_parse_log_output_empty_sha_skipped(self) -> None:
        """Record with empty sha field is skipped."""
        output = _make_log_output(sha="", short_sha="a" * 7)
        commits = _parse_log_output(output)
        assert len(commits) == 0
