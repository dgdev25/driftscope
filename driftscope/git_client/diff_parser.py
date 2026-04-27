"""Unified diff parser for git diff output.

Parses unified diff format into structured FileHunk objects with
line-level add/remove tracking.

Time Complexity: O(n) where n is the number of lines in the diff.
Space Complexity: O(m) where m is the number of added/removed lines.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

_RE_FILE_HEADER = re.compile(r"^\+\+\+ b/(.+)$")
_RE_HUNK_HEADER = re.compile(
    r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@"
)


@dataclass(frozen=True)
class FileHunk:
    """Parsed diff information for a single file.

    Attributes:
        file_path: Path of the file relative to repo root.
        added_lines: Line numbers added in the new version.
        removed_lines: Line numbers removed from the old version.
    """

    file_path: str
    added_lines: list[int] = field(default_factory=list)
    removed_lines: list[int] = field(default_factory=list)


def parse_unified_diff(diff_text: str) -> list[FileHunk]:
    """Parse a unified diff string into FileHunk objects.

    Handles multi-file diffs, multiple hunks per file, and pure
    addition/deletion hunks (count=0).

    Args:
        diff_text: Raw unified diff output (e.g., from ``git diff``).

    Returns:
        List of FileHunk objects, one per file touched in the diff.

    Example:
        >>> parse_unified_diff("+++ b/main.py\\n@@ -1 +1,2 @@\\n+x\\n")
        [FileHunk(file_path='main.py', added_lines=[1], removed_lines=[])]
    """
    if not diff_text:
        return []

    hunks_by_file: dict[str, dict[str, list[int]]] = {}
    current_file: str | None = None
    current_added: list[int] | None = None
    current_removed: list[int] | None = None
    old_line = 0
    new_line = 0

    for raw_line in diff_text.splitlines():
        file_match = _RE_FILE_HEADER.match(raw_line)
        if file_match:
            current_file = file_match.group(1)
            if current_file not in hunks_by_file:
                hunks_by_file[current_file] = {"added": [], "removed": []}
            current_added = hunks_by_file[current_file]["added"]
            current_removed = hunks_by_file[current_file]["removed"]
            continue

        hunk_match = _RE_HUNK_HEADER.match(raw_line)
        if hunk_match:
            old_start = int(hunk_match.group(1))
            new_start = int(hunk_match.group(3))
            old_line = old_start
            new_line = new_start
            continue

        if current_file is None or current_added is None or current_removed is None:
            continue

        if raw_line.startswith("+"):
            current_added.append(new_line)
            new_line += 1
        elif raw_line.startswith("-"):
            current_removed.append(old_line)
            old_line += 1
        elif raw_line.startswith(" ") or raw_line == "":
            # Context line or empty line within a hunk
            old_line += 1
            new_line += 1

    return [
        FileHunk(
            file_path=fpath,
            added_lines=data["added"],
            removed_lines=data["removed"],
        )
        for fpath, data in hunks_by_file.items()
    ]
