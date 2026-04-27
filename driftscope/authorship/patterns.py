"""Built-in co-authorship tag regex patterns for AI attribution."""

import re


BUILTIN_PATTERN_DEFS: list[tuple[str, str]] = [
    ("github_copilot", r"Co-Authored-By:\s*GitHub\s+Copilot"),
    ("claude_code", r"Co-Authored-By:\s*Claude"),
    ("cursor_ai", r"Co-Authored-By:\s*Cursor"),
    ("devin", r"Co-Authored-By:\s*Devin"),
    ("ai_generated_trailer", r"AI-Generated:\s*.+"),
]


def _compile_builtins() -> list[tuple[str, re.Pattern[str]]]:
    return [(name, re.compile(pat, re.IGNORECASE)) for name, pat in BUILTIN_PATTERN_DEFS]


BUILTIN_PATTERNS: list[tuple[str, re.Pattern[str]]] = _compile_builtins()


def compile_patterns(
    custom_patterns: list[str] | None = None,
    include_builtins: bool = True,
) -> list[tuple[str, re.Pattern[str]]]:
    """Compile built-in and optional custom regex patterns for AI attribution.

    Args:
        custom_patterns: Additional regex patterns to match against commit messages.
        include_builtins: Whether to include the built-in co-authorship patterns.

    Returns:
        List of (name, compiled_pattern) tuples in matching order.

    Raises:
        ValueError: If any custom pattern fails to compile.

    Example:
        >>> patterns = compile_patterns(custom_patterns=[r"MyBot:\\s*\\w+"])
        >>> len(patterns) > 0
        True
    """
    patterns: list[tuple[str, re.Pattern[str]]] = []

    if include_builtins:
        patterns.extend(BUILTIN_PATTERNS)

    if custom_patterns:
        for raw in custom_patterns:
            try:
                patterns.append((raw, re.compile(raw, re.IGNORECASE)))
            except re.error as e:
                raise ValueError(f"Cannot compile pattern '{raw}': {e}") from e

    return patterns
