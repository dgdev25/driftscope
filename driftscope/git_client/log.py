"""Git log parser for commit history extraction.

Parses ``git log`` output with a custom null-byte-delimited format into
Commit objects.

Time Complexity: O(n) where n is the number of commits.
Space Complexity: O(n) for the commit list.
"""

from __future__ import annotations

import subprocess
from datetime import datetime
from pathlib import Path

from driftscope.errors import GitError
from driftscope.models.commit import Commit

_LOG_FORMAT = "%H%n%h%n%aI%n%an%n%ae%n%cN%n%ce%n%s%n%b%x00"

_NUM_FIELDS = 9  # sha, short_sha, timestamp, author_name, author_email,
# committer_name, committer_email, subject, body


def parse_log(
    repo_path: Path,
    from_ref: str | None = None,
    to_ref: str | None = None,
    since: str | None = None,
) -> list[Commit]:
    """Parse git log for a repository or ref range.

    Args:
        repo_path: Absolute path to the git repository root.
        from_ref: Starting ref (exclusive) for range queries.
        to_ref: Ending ref (inclusive) for range queries.
        since: ISO 8601 date string for ``--since`` filter.

    Returns:
        List of Commit objects in oldest-first order.

    Raises:
        GitError: If git is unavailable or the repo is invalid.
    """
    cmd: list[str] = [
        "git",
        "-C",
        str(repo_path),
        "log",
        f"--format={_LOG_FORMAT}",
    ]

    if since:
        cmd.append(f"--since={since}")

    if from_ref and to_ref:
        cmd.append(f"{from_ref}..{to_ref}")
    elif to_ref:
        cmd.append(to_ref)

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120,
            check=True,
        )
    except FileNotFoundError:
        raise GitError(
            "git binary not found on PATH",
            suggestion="Install git >= 2.30 and ensure it is on your PATH",
        )
    except subprocess.TimeoutExpired:
        raise GitError(
            "git log timed out",
            suggestion="Try narrowing the ref range or using --since",
        )
    except subprocess.CalledProcessError as exc:
        raise GitError(
            f"git log failed: {exc.stderr.strip()}",
            suggestion="Ensure the repository exists and refs are valid",
        )

    return _parse_log_output(result.stdout)


def _parse_log_output(output: str) -> list[Commit]:
    """Parse null-delimited git log output into Commit objects.

    The log format produces 9 fields per commit separated by newlines,
    with commits delimited by null bytes. Parent SHAs are extracted
    from the commit body (lines starting with "parent").

    Args:
        output: Raw stdout from git log with custom format.

    Returns:
        List of Commit objects in oldest-first order.
    """
    if not output.strip():
        return []

    commits: list[Commit] = []
    records = output.split("\x00")

    for record in records:
        record = record.strip()
        if not record:
            continue

        fields = record.split("\n", maxsplit=_NUM_FIELDS - 1)
        if len(fields) < _NUM_FIELDS - 1:
            # Minimum: 8 fields (body may be empty and not split)
            continue

        sha = fields[0].strip()
        short_sha = fields[1].strip()
        timestamp_str = fields[2].strip()
        author_name = fields[3].strip()
        author_email = fields[4].strip()
        committer_name = fields[5].strip()
        committer_email = fields[6].strip()
        message_subject = fields[7].strip()

        # Body is the last field — may contain newlines
        message_body = fields[8].strip() if len(fields) > 8 else ""

        if not sha or not short_sha:
            continue

        try:
            timestamp = datetime.fromisoformat(timestamp_str)
        except (ValueError, TypeError):
            continue

        # Extract parent SHAs from the body (not typically in format output,
        # but we parse them if present in message_body)
        parent_shas: list[str] = []
        for line in message_body.splitlines():
            if line.startswith("parent "):
                parent_sha = line.split(" ", 1)[1].strip()
                if len(parent_sha) >= 40:
                    parent_shas.append(parent_sha[:40])

        commits.append(
            Commit(
                sha=sha,
                short_sha=short_sha,
                timestamp=timestamp,
                author_name=author_name,
                author_email=author_email,
                committer_name=committer_name,
                committer_email=committer_email,
                message_subject=message_subject,
                message_body=message_body,
                parent_shas=parent_shas,
            )
        )

    # Reverse to oldest-first (git log outputs newest-first)
    commits.reverse()
    return commits


def is_bare_repo(repo_path: Path) -> bool:
    """Check whether a path points to a bare git repository.

    Args:
        repo_path: Absolute path to check.

    Returns:
        True if the path is a bare git repository, False otherwise.

    Raises:
        GitError: If git is unavailable.
    """
    try:
        result = subprocess.run(
            ["git", "-C", str(repo_path), "config", "core.bare"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except FileNotFoundError:
        raise GitError(
            "git binary not found on PATH",
            suggestion="Install git >= 2.30 and ensure it is on your PATH",
        )
    except subprocess.TimeoutExpired:
        raise GitError(
            "git config timed out",
            suggestion="Check your git installation",
        )

    return result.stdout.strip().lower() == "true"
