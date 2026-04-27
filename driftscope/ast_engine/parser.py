"""AST parsing via tree-sitter with lazy language loading.

Provides source code parsing, language resolution, and text hashing
for the AST diff pipeline. Languages are loaded on first use and cached
in a module-level registry.
"""

from __future__ import annotations

import hashlib
import importlib

from driftscope.errors import ASTParseError

try:
    import tree_sitter as _tree_sitter_mod
except ImportError:  # pragma: no cover — grammar packages not installed
    _tree_sitter_mod = None  # type: ignore[assignment]

SUPPORTED_LANGUAGES: dict[str, str] = {
    "python": "tree_sitter_python",
    "typescript": "tree_sitter_typescript",
    "javascript": "tree_sitter_javascript",
    "go": "tree_sitter_go",
    "java": "tree_sitter_java",
    "ruby": "tree_sitter_ruby",
}

_language_registry: dict[str, object] = {}


def get_language(language: str) -> object:
    """Resolve a tree-sitter Language object for the given language name.

    Uses a module-level cache to avoid re-importing grammar bindings on
    repeated calls.

    Args:
        language: One of the keys in SUPPORTED_LANGUAGES
            (e.g. ``"python"``, ``"go"``).

    Returns:
        A ``tree_sitter.Language`` instance for the requested language.

    Raises:
        ASTParseError: If the language is not supported or its grammar
            binding cannot be imported.
    """
    if language not in SUPPORTED_LANGUAGES:
        raise ASTParseError(
            f"Unsupported language: {language!r}. "
            f"Supported: {sorted(SUPPORTED_LANGUAGES)}",
        )

    if language in _language_registry:
        return _language_registry[language]

    module_name = SUPPORTED_LANGUAGES[language]
    try:
        mod = importlib.import_module(module_name)
    except ImportError:
        raise ASTParseError(
            f"Grammar binding {module_name!r} is not installed. "
            f"Install it with: pip install {module_name}",
        )

    if _tree_sitter_mod is None:
        raise ASTParseError(
            "tree-sitter core library is not installed. "
            "Install it with: pip install tree-sitter",
        )
    try:
        lang_func = getattr(mod, "language")
        lang = _tree_sitter_mod.Language(lang_func())
    except (AttributeError, TypeError, ValueError) as exc:
        raise ASTParseError(
            f"Failed to create Language from {module_name!r}: {exc}",
        )

    _language_registry[language] = lang
    return lang


def parse_source(
    source: str,
    language: str,
    timeout: int = 5000,
) -> object:
    """Parse source code into a tree-sitter Tree.

    Args:
        source: Source code text to parse.
        language: Language identifier (must be in SUPPORTED_LANGUAGES).
        timeout: Parse timeout in microseconds (default 5000).

    Returns:
        A ``tree_sitter.Tree`` instance.

    Raises:
        ASTParseError: If the language is unsupported, the grammar is
            unavailable, or parsing produces a null tree.
    """
    lang = get_language(language)

    # get_language() already validated that _tree_sitter_mod is available
    parser = _tree_sitter_mod.Parser()
    parser.language = lang
    parser.timeout_micros = timeout

    tree = parser.parse(source.encode("utf-8"))
    if tree is None:
        raise ASTParseError(
            f"tree-sitter returned None for {language} source "
            f"(timeout={timeout}us)",
        )
    return tree


def compute_text_hash(text: str) -> str:
    """Compute a SHA-256 hex digest of the given text.

    Args:
        text: Input string to hash.

    Returns:
        64-character lowercase hex digest.

    Time Complexity: O(n) where n = len(text)
    Space Complexity: O(1) additional
    """
    return hashlib.sha256(text.encode("utf-8")).hexdigest()
