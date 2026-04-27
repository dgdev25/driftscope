"""Authorship attribution — human/AI commit classification."""

from driftscope.authorship.patterns import BUILTIN_PATTERNS, compile_patterns
from driftscope.authorship.classifier import classify_commit, classify_history

__all__ = ["BUILTIN_PATTERNS", "compile_patterns", "classify_commit", "classify_history"]
