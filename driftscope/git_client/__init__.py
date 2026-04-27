"""Git client — blame, log, and diff parsing via local git binary."""

from driftscope.git_client.blame import run_blame
from driftscope.git_client.diff_parser import FileHunk, parse_unified_diff
from driftscope.git_client.log import parse_log

__all__ = [
    "run_blame",
    "parse_log",
    "parse_unified_diff",
    "FileHunk",
]
