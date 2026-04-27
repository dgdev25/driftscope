"""Git blame porcelain parser.

Runs ``git blame --porcelain`` and parses the structured output into
BlameLine objects.

Time Complexity: O(n) where n is the number of lines in the blame output.
Space Complexity: O(m) where m is the number of lines in the file.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

from driftscope.errors import GitError
from driftscope.models.blame import BlameLine

_RE_SHA_HEADER_FULL = re.compile(r"^([0-9a-f]{40})\s+(\d+)\s+(\d+)\s+(\d+)")
_RE_SHA_HEADER_SHORT = re.compile(r"^([0-9a-f]{40})\s+(\d+)\s+(\d+)$")
_RE_AUTHOR = re.compile(r"^author (.+)$")
_RE_AUTHOR_MAIL = re.compile(r"^author-mail <(.+)>$")
_RE_CONTENT = re.compile(r"^\t(.*)$")


def _check_git_available() -> None:
    """Verify that the git binary is available and meets minimum version.

    Raises:
        GitError: If git is not found on PATH or times out.
    """
    try:
        subprocess.run(
            ["git", "--version"],
            capture_output=True,
            text=True,
            timeout=10,
            check=True,
        )
    except FileNotFoundError:
        raise GitError(
            "git binary not found on PATH",
            suggestion="Install git >= 2.30 and ensure it is on your PATH",
        )
    except subprocess.TimeoutExpired:
        raise GitError(
            "git --version timed out",
            suggestion="Check your git installation for issues",
        )


def run_blame(
    repo_path: Path,
    file_path: str,
    revision: str = "HEAD",
) -> list[BlameLine]:
    """Run git blame --porcelain on a single file and return parsed lines.

    Args:
        repo_path: Absolute path to the git repository root.
        file_path: Path to the file relative to repo root.
        revision: Git revision to blame at (default: HEAD).

    Returns:
        List of BlameLine objects, one per line in the file.

    Raises:
        GitError: If git is unavailable, the repo is invalid, or the
            file does not exist at the given revision.
    """
    _check_git_available()

    try:
        result = subprocess.run(
            ["git", "-C", str(repo_path), "blame", "--porcelain", revision, "--", file_path],
            capture_output=True,
            text=True,
            timeout=60,
            check=True,
        )
    except FileNotFoundError:
        raise GitError(
            "git binary not found on PATH",
            suggestion="Install git >= 2.30 and ensure it is on your PATH",
        )
    except subprocess.TimeoutExpired:
        raise GitError(
            f"git blame timed out for {file_path}@{revision}",
            suggestion="The file may be very large; try a narrower revision range",
        )
    except subprocess.CalledProcessError as exc:
        raise GitError(
            f"git blame failed for {file_path}@{revision}: {exc.stderr.strip()}",
            file=file_path,
            suggestion="Ensure the file exists at the given revision",
        )

    return _parse_porcelain(result.stdout)


def _parse_porcelain(output: str) -> list[BlameLine]:
    """Parse git blame --porcelain output into BlameLine objects.

    The porcelain format repeats this structure for each line in the file::

        <sha> <orig_line> <final_line> <num_lines>
        author <name>
        author-mail <<email>>
        ...
        \\t<content>

    When consecutive lines share the same commit, subsequent entries
    omit the author/mail headers and use a 3-field SHA header::

        <sha> <orig_line> <final_line>
        \\t<content>

    The parser carries over author info from the previous commit entry
    when headers are absent.

    Args:
        output: Raw stdout from ``git blame --porcelain``.

    Returns:
        List of BlameLine objects in file order.
    """
    lines: list[BlameLine] = []
    current_sha: str | None = None
    final_line: int | None = None
    author_name: str | None = None
    author_email: str | None = None
    # Track the last known author info for carry-over on repeat entries
    last_author_name: str | None = None
    last_author_email: str | None = None
    last_sha: str | None = None

    for raw_line in output.splitlines():
        # Try full 4-field header first (new commit entry)
        sha_full = _RE_SHA_HEADER_FULL.match(raw_line)
        if sha_full:
            current_sha = sha_full.group(1)
            final_line = int(sha_full.group(3))
            author_name = None
            author_email = None
            continue

        # Try short 3-field header (repeat of same commit)
        sha_short = _RE_SHA_HEADER_SHORT.match(raw_line)
        if sha_short:
            current_sha = sha_short.group(1)
            final_line = int(sha_short.group(3))
            # Carry over author from previous entry if same commit
            if current_sha == last_sha:
                author_name = last_author_name
                author_email = last_author_email
            else:
                author_name = None
                author_email = None
            continue

        if current_sha is None:
            continue

        author_match = _RE_AUTHOR.match(raw_line)
        if author_match:
            author_name = author_match.group(1)
            continue

        mail_match = _RE_AUTHOR_MAIL.match(raw_line)
        if mail_match:
            author_email = mail_match.group(1)
            continue

        content_match = _RE_CONTENT.match(raw_line)
        if content_match and final_line is not None:
            content = content_match.group(1)
            assert author_name is not None, f"Missing author for line {final_line}"
            assert author_email is not None, f"Missing email for line {final_line}"
            lines.append(
                BlameLine(
                    line_number=final_line,
                    commit_sha=current_sha,
                    author_name=author_name,
                    author_email=author_email,
                    content=content,
                )
            )
            # Save for carry-over on next entry
            last_sha = current_sha
            last_author_name = author_name
            last_author_email = author_email
            # Reset state for next entry
            current_sha = None
            final_line = None
            author_name = None
            author_email = None

    return lines
