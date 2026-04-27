"""Commit classification engine — human vs. AI attribution."""

from driftscope.authorship.patterns import compile_patterns
from driftscope.models.commit import Commit
from driftscope.models.history import AttributedCommit, AttributedHistory, CommitHistory


def classify_commit(
    commit: Commit,
    patterns: list[tuple[str, str]],
) -> AttributedCommit:
    """Classify a single commit as human or AI-authored.

    Searches the commit subject and body against the provided regex patterns.
    The first matching pattern determines the classification.

    Args:
        commit: The commit to classify.
        patterns: List of (name, compiled_regex) tuples to match against.

    Returns:
        AttributedCommit with authorship_class set to "ai" or "human".

    Time Complexity: O(P * M) where P = number of patterns, M = message length.
    Space Complexity: O(1) beyond the output object.
    """
    full_message = f"{commit.message_subject}\n{commit.message_body}"

    for pattern_name, pattern in patterns:
        match = pattern.search(full_message)
        if match:
            return AttributedCommit(
                **commit.model_dump(),
                authorship_class="ai",
                matched_pattern=pattern_name,
                matched_text=match.group(0),
            )

    return AttributedCommit(
        **commit.model_dump(),
        authorship_class="human",
    )


def classify_history(
    history_commit_data: CommitHistory,
    custom_patterns: list[str] | None = None,
    include_builtins: bool = True,
) -> AttributedHistory:
    """Classify all commits in a history and compute aggregate counts.

    Args:
        history_commit_data: The commit history to classify.
        custom_patterns: Additional regex patterns for AI detection.
        include_builtins: Whether to include built-in co-authorship patterns.

    Returns:
        AttributedHistory with per-commit classification and aggregate counts.

    Time Complexity: O(N * P * M) where N = number of commits.
    Space Complexity: O(N) for the attributed commits list.
    """
    patterns = compile_patterns(custom_patterns, include_builtins)

    attributed = [classify_commit(c, patterns) for c in history_commit_data.commits]
    ai_count = sum(1 for c in attributed if c.authorship_class == "ai")
    human_count = len(attributed) - ai_count

    return AttributedHistory(
        repo_path=history_commit_data.repo_path,
        commits=attributed,
        blame=history_commit_data.blame,
        range_start=history_commit_data.range_start,
        range_end=history_commit_data.range_end,
        ai_commit_count=ai_count,
        human_commit_count=human_count,
    )
