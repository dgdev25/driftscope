"""Tests for co-authorship tag regex patterns."""

import re

import pytest

from driftscope.authorship.patterns import BUILTIN_PATTERNS, BUILTIN_PATTERN_DEFS, compile_patterns


class TestBuiltinPatterns:
    @pytest.mark.parametrize("name,pattern_str", BUILTIN_PATTERN_DEFS)
    def test_pattern_compiles(self, name: str, pattern_str: str) -> None:
        compiled = re.compile(pattern_str, re.IGNORECASE)
        assert compiled is not None

    def test_github_copilot_matches(self) -> None:
        _, pat = BUILTIN_PATTERNS[0]
        assert pat.search("Co-Authored-By: GitHub Copilot")
        assert pat.search("Co-Authored-By: github copilot")

    def test_github_copilot_rejects_non_copilot(self) -> None:
        _, pat = BUILTIN_PATTERNS[0]
        assert not pat.search("Co-Authored-By: Alice")

    def test_claude_code_matches(self) -> None:
        _, pat = BUILTIN_PATTERNS[1]
        assert pat.search("Co-Authored-By: Claude")
        assert pat.search("Co-Authored-By: claude")

    def test_cursor_ai_matches(self) -> None:
        _, pat = BUILTIN_PATTERNS[2]
        assert pat.search("Co-Authored-By: Cursor")

    def test_devin_matches(self) -> None:
        _, pat = BUILTIN_PATTERNS[3]
        assert pat.search("Co-Authored-By: Devin")

    def test_ai_generated_trailer_matches(self) -> None:
        _, pat = BUILTIN_PATTERNS[4]
        assert pat.search("AI-Generated: Payment processing function")
        assert pat.search("ai-generated: test")

    def test_ai_generated_rejects_empty(self) -> None:
        _, pat = BUILTIN_PATTERNS[4]
        assert not pat.search("AI-Generated:")


class TestCompilePatterns:
    def test_builtins_only(self) -> None:
        patterns = compile_patterns()
        assert len(patterns) == len(BUILTIN_PATTERN_DEFS)

    def test_builtins_excluded(self) -> None:
        patterns = compile_patterns(include_builtins=False, custom_patterns=[r"AI:\s*\w+"])
        assert len(patterns) == 1

    def test_custom_appended(self) -> None:
        patterns = compile_patterns(custom_patterns=[r"MyAI:\s*\w+"])
        assert len(patterns) == len(BUILTIN_PATTERN_DEFS) + 1

    def test_invalid_custom_raises(self) -> None:
        with pytest.raises(ValueError, match="Cannot compile pattern"):
            compile_patterns(custom_patterns=["[unclosed"])

    def test_no_patterns_at_all(self) -> None:
        patterns = compile_patterns(include_builtins=False)
        assert len(patterns) == 0
