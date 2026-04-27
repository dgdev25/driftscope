"""Tests for driftscope.git_client.blame."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from driftscope.errors import GitError
from driftscope.git_client.blame import (
    _check_git_available,
    _parse_porcelain,
    run_blame,
)
from driftscope.models.blame import BlameLine


class TestParsePorcelain:
    """Unit tests for _parse_porcelain."""

    def test_single_line(self) -> None:
        output = (
            "a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0 1 1 1\n"
            "author Alice Smith\n"
            "author-mail <alice@example.com>\n"
            "author-time 1700000000\n"
            "author-tz +0000\n"
            "\thello world\n"
        )
        result = _parse_porcelain(output)
        assert len(result) == 1
        assert result[0] == BlameLine(
            line_number=1,
            commit_sha="a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0",
            author_name="Alice Smith",
            author_email="alice@example.com",
            content="hello world",
        )

    def test_multiple_lines(self) -> None:
        output = (
            "a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f89012 1 1 2\n"
            "author Bob\n"
            "author-mail <bob@test.com>\n"
            "\tline one\n"
            "f9e8d7c6b5a4f3e2d1c0b9a8f7e6d5c4b3a2f1e0 2 2 1\n"
            "author Carol\n"
            "author-mail <carol@test.com>\n"
            "\tline two\n"
        )
        result = _parse_porcelain(output)
        assert len(result) == 2
        assert result[0].author_name == "Bob"
        assert result[0].content == "line one"
        assert result[1].author_name == "Carol"
        assert result[1].content == "line two"

    def test_empty_output(self) -> None:
        result = _parse_porcelain("")
        assert result == []

    def test_header_lines_without_content_skipped(self) -> None:
        """Lines that have SHA/author but no TAB-content should not produce BlameLine."""
        output = (
            "aaa111bbb222ccc333ddd444eee555fff666aaa777 1 1 1\n"
            "author Dave\n"
            "author-mail <dave@test.com>\n"
            "filename test.py\n"
        )
        result = _parse_porcelain(output)
        assert result == []

    def test_renamed_boundary_info_ignored(self) -> None:
        """Extra porcelain headers like 'summary' and 'boundary' are ignored."""
        output = (
            "a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0 1 1 1\n"
            "author Eve\n"
            "author-mail <eve@test.com>\n"
            "summary added feature\n"
            "boundary\n"
            "\tcode here\n"
        )
        result = _parse_porcelain(output)
        assert len(result) == 1
        assert result[0].content == "code here"


class TestRunBlame:
    """Tests for run_blame with mocked subprocess."""

    def test_run_blame_success(self) -> None:
        porcelain = (
            "a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0 1 1 1\n"
            "author Alice\n"
            "author-mail <alice@x.com>\n"
            "\tcontent\n"
        )
        mock_version = MagicMock()
        mock_version.stdout = "git version 2.40.0\n"
        mock_blame = MagicMock()
        mock_blame.stdout = porcelain

        with patch(
            "driftscope.git_client.blame.subprocess.run",
            side_effect=[mock_version, mock_blame],
        ):
            lines = run_blame(Path("/repo"), "main.py", "HEAD")

        assert len(lines) == 1
        assert lines[0].content == "content"

    def test_run_blame_git_not_found(self) -> None:
        with patch(
            "driftscope.git_client.blame.subprocess.run",
            side_effect=FileNotFoundError,
        ):
            with pytest.raises(GitError, match="git binary not found"):
                run_blame(Path("/repo"), "main.py")

    def test_run_blame_timeout(self) -> None:
        import subprocess

        mock_version = MagicMock()
        mock_version.stdout = "git version 2.40.0\n"

        with patch(
            "driftscope.git_client.blame.subprocess.run",
            side_effect=[mock_version, subprocess.TimeoutExpired(cmd="git", timeout=60)],
        ):
            with pytest.raises(GitError, match="timed out"):
                run_blame(Path("/repo"), "main.py")

    def test_run_blame_git_error(self) -> None:
        import subprocess

        error = subprocess.CalledProcessError(
            returncode=128, cmd="git", stderr="fatal: no such path"
        )
        mock_version = MagicMock()
        mock_version.stdout = "git version 2.40.0\n"

        with patch(
            "driftscope.git_client.blame.subprocess.run",
            side_effect=[mock_version, error],
        ):
            with pytest.raises(GitError, match="git blame failed"):
                run_blame(Path("/repo"), "nonexistent.py")


class TestCheckGitAvailable:
    """Tests for _check_git_available."""

    def test_git_available(self) -> None:
        mock_result = MagicMock()
        mock_result.stdout = "git version 2.40.0\n"
        with patch("driftscope.git_client.blame.subprocess.run", return_value=mock_result):
            _check_git_available()  # Should not raise

    def test_git_not_found(self) -> None:
        with patch(
            "driftscope.git_client.blame.subprocess.run",
            side_effect=FileNotFoundError,
        ):
            with pytest.raises(GitError, match="git binary not found"):
                _check_git_available()

    def test_git_timeout(self) -> None:
        import subprocess

        with patch(
            "driftscope.git_client.blame.subprocess.run",
            side_effect=subprocess.TimeoutExpired(cmd="git", timeout=10),
        ):
            with pytest.raises(GitError, match="timed out"):
                _check_git_available()
