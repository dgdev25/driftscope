"""AST Engine module — tree-sitter parsing, diffing, and survival analysis.

Exports:
    parse_source: Parse source code into a tree-sitter Tree.
    get_language: Resolve a tree-sitter Language for a supported language.
    compute_ast_diff: Compute AST-level diff between two source versions.
    compute_survival: Compute line survival rates from diffs and blame.
"""

from driftscope.ast_engine.differ import compute_ast_diff
from driftscope.ast_engine.parser import get_language, parse_source
from driftscope.ast_engine.survival import compute_survival

__all__ = [
    "compute_ast_diff",
    "compute_survival",
    "get_language",
    "parse_source",
]
