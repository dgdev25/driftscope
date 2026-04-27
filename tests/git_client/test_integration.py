"""Integration tests for driftscope.git_client against real git repos.

Uses the tmp_git_repo fixture to run actual git commands and verify
end-to-end behavior.
"""

import subprocess
from pathlib import Path

import pytest

from driftscope.git_client.blame import run_blame
from driftscope.git_client.diff_parser import parse_unified_diff
from driftscope.git_client.log import is_bare_repo, parse_log


class TestLogIntegration:
    """Integration tests for parse_log with real git repos."""

    def test_parse_log_single_commit(self, tmp_git_repo: Path) -> None:
        commits = parse_log(tmp_git_repo)
        assert len(commits) >= 1
        assert commits[0].message_subject == "Initial commit"
        assert len(commits[0].sha) == 40
        assert len(commits[0].short_sha) == 7
        assert commits[0].author_name == "Test User"
        assert commits[0].author_email == "test@example.com"

    def test_parse_log_multiple_commits(self, tmp_git_repo: Path) -> None:
        # Create additional commits
        for i in range(3):
            f = tmp_git_repo / f"file{i}.py"
            f.write_text(f"# file {i}\n")
            subprocess.run(
                ["git", "add", f"file{i}.py"],
                cwd=tmp_git_repo,
                check=True,
                capture_output=True,
            )
            subprocess.run(
                ["git", "commit", "-m", f"Add file{i}"],
                cwd=tmp_git_repo,
                check=True,
                capture_output=True,
            )

        commits = parse_log(tmp_git_repo)
        assert len(commits) == 4  # Initial + 3 additions
        # Oldest first
        assert commits[0].message_subject == "Initial commit"
        assert commits[-1].message_subject == "Add file2"


class TestBlameIntegration:
    """Integration tests for run_blame with real git repos."""

    def test_run_blame_on_committed_file(self, tmp_git_repo: Path) -> None:
        # Add a file with known content
        code_file = tmp_git_repo / "example.py"
        code_file.write_text("def hello():\n    return 'world'\n")
        subprocess.run(
            ["git", "add", "example.py"],
            cwd=tmp_git_repo,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "commit", "-m", "Add example"],
            cwd=tmp_git_repo,
            check=True,
            capture_output=True,
        )

        lines = run_blame(tmp_git_repo, "example.py")
        assert len(lines) == 2
        assert lines[0].line_number == 1
        assert "def hello" in lines[0].content
        assert lines[0].author_name == "Test User"


class TestDiffIntegration:
    """Integration tests for parse_unified_diff with real git diffs."""

    def test_parse_real_git_diff(self, tmp_git_repo: Path) -> None:
        # Create initial file
        code_file = tmp_git_repo / "calc.py"
        code_file.write_text("x = 1\ny = 2\n")
        subprocess.run(
            ["git", "add", "calc.py"],
            cwd=tmp_git_repo,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "commit", "-m", "Add calc"],
            cwd=tmp_git_repo,
            check=True,
            capture_output=True,
        )

        # Modify the file
        code_file.write_text("x = 1\nz = 3\ny = 2\n")

        # Get the unstaged diff
        result = subprocess.run(
            ["git", "diff", "--", "calc.py"],
            cwd=tmp_git_repo,
            capture_output=True,
            text=True,
            check=True,
        )

        hunks = parse_unified_diff(result.stdout)
        assert len(hunks) == 1
        assert hunks[0].file_path == "calc.py"
        assert len(hunks[0].added_lines) >= 1
        assert len(hunks[0].removed_lines) >= 0


class TestIsBareRepoIntegration:
    """Integration tests for is_bare_repo."""

    def test_non_bare_repo(self, tmp_git_repo: Path) -> None:
        assert is_bare_repo(tmp_git_repo) is False

    def test_bare_repo(self, tmp_path: Path) -> None:
        subprocess.run(
            ["git", "init", "--bare"],
            cwd=tmp_path,
            check=True,
            capture_output=True,
        )
        assert is_bare_repo(tmp_path) is True
