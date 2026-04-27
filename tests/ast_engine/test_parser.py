"""Tests for driftscope.ast_engine.parser."""

from unittest.mock import MagicMock, patch

import pytest

from driftscope.ast_engine.parser import (
    SUPPORTED_LANGUAGES,
    compute_text_hash,
    get_language,
    parse_source,
    _language_registry,
)
from driftscope.errors import ASTParseError


# ---------------------------------------------------------------------------
# get_language
# ---------------------------------------------------------------------------


class TestGetLanguage:
    """Tests for the get_language function."""

    def test_unsupported_language_raises(self) -> None:
        """Requesting an unsupported language must raise ASTParseError."""
        with pytest.raises(ASTParseError, match="Unsupported language"):
            get_language("brainfuck")

    def test_missing_grammar_binding_raises(self) -> None:
        """If the grammar package is not installed, raise ASTParseError."""
        _language_registry.pop("python", None)
        with pytest.raises(ASTParseError, match="Grammar binding"):
            get_language("python")

    @patch("driftscope.ast_engine.parser._tree_sitter_mod")
    def test_successful_language_load(self, mock_ts: MagicMock) -> None:
        """Successful grammar import and Language creation."""
        _language_registry.pop("python", None)

        fake_lang = MagicMock(name="Language")
        mock_ts.Language.return_value = fake_lang

        with patch("importlib.import_module") as mock_import:
            mock_mod = MagicMock()
            mock_mod.language.return_value = "lang_data"
            mock_import.return_value = mock_mod

            result = get_language("python")

        assert result is fake_lang
        mock_ts.Language.assert_called_once_with("lang_data")
        # Now cached
        assert "python" in _language_registry

    @patch("driftscope.ast_engine.parser._tree_sitter_mod")
    def test_returns_cached_language(self, mock_ts: MagicMock) -> None:
        """Second call for same language returns cached entry without import."""
        cached = MagicMock(name="CachedLang")
        _language_registry["go"] = cached

        result = get_language("go")
        assert result is cached

        # Cleanup
        del _language_registry["go"]

    @patch("driftscope.ast_engine.parser._tree_sitter_mod", new=None)
    def test_tree_sitter_none_raises(self) -> None:
        """If _tree_sitter_mod is None, get_language raises ASTParseError."""
        _language_registry.pop("ruby", None)
        with patch("importlib.import_module") as mock_import:
            mock_mod = MagicMock()
            mock_mod.language.return_value = "lang_data"
            mock_import.return_value = mock_mod

            with pytest.raises(ASTParseError, match="tree-sitter core library"):
                get_language("ruby")

    @patch("driftscope.ast_engine.parser._tree_sitter_mod")
    def test_language_creation_failure_raises(self, mock_ts: MagicMock) -> None:
        """If Language() raises, get_language raises ASTParseError."""
        _language_registry.pop("java", None)
        mock_ts.Language.side_effect = TypeError("bad lang data")

        with patch("importlib.import_module") as mock_import:
            mock_mod = MagicMock()
            mock_mod.language.return_value = "bad_data"
            mock_import.return_value = mock_mod

            with pytest.raises(ASTParseError, match="Failed to create Language"):
                get_language("java")


# ---------------------------------------------------------------------------
# compute_text_hash
# ---------------------------------------------------------------------------


class TestComputeTextHash:
    """Tests for compute_text_hash."""

    def test_returns_64_char_hex(self) -> None:
        """SHA-256 hex digest must be 64 lowercase hex chars."""
        h = compute_text_hash("hello")
        assert len(h) == 64
        assert all(c in "0123456789abcdef" for c in h)

    def test_deterministic(self) -> None:
        """Same input must produce same hash across calls."""
        assert compute_text_hash("abc") == compute_text_hash("abc")

    def test_different_inputs_differ(self) -> None:
        """Different inputs must produce different hashes."""
        assert compute_text_hash("foo") != compute_text_hash("bar")

    def test_empty_string(self) -> None:
        """Empty string must produce a valid SHA-256 hash."""
        h = compute_text_hash("")
        assert len(h) == 64
        assert h == "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"


# ---------------------------------------------------------------------------
# parse_source
# ---------------------------------------------------------------------------


class TestParseSource:
    """Tests for parse_source with mocked tree-sitter."""

    @patch("driftscope.ast_engine.parser.get_language")
    @patch("driftscope.ast_engine.parser._tree_sitter_mod")
    def test_returns_tree_on_success(
        self,
        mock_ts: MagicMock,
        mock_get_lang: MagicMock,
    ) -> None:
        """Successful parse must return the tree from the parser."""
        fake_tree = MagicMock(name="Tree")
        fake_parser = MagicMock(name="Parser")
        fake_parser.parse.return_value = fake_tree
        mock_ts.Parser.return_value = fake_parser
        mock_get_lang.return_value = MagicMock(name="Language")

        result = parse_source("x = 1", "python")
        assert result is fake_tree

    @patch("driftscope.ast_engine.parser.get_language")
    @patch("driftscope.ast_engine.parser._tree_sitter_mod")
    def test_raises_on_none_tree(
        self,
        mock_ts: MagicMock,
        mock_get_lang: MagicMock,
    ) -> None:
        """If parser.parse returns None, raise ASTParseError."""
        fake_parser = MagicMock(name="Parser")
        fake_parser.parse.return_value = None
        mock_ts.Parser.return_value = fake_parser
        mock_get_lang.return_value = MagicMock(name="Language")

        with pytest.raises(ASTParseError, match="returned None"):
            parse_source("x = 1", "python", timeout=1000)

    @patch("driftscope.ast_engine.parser.get_language")
    @patch("driftscope.ast_engine.parser._tree_sitter_mod", new=None)
    def test_raises_when_tree_sitter_mod_is_none(
        self,
        mock_get_lang: MagicMock,
    ) -> None:
        """If _tree_sitter_mod is None, raise ASTParseError."""
        with pytest.raises(ASTParseError, match="tree-sitter core library"):
            parse_source("x = 1", "python")


# ---------------------------------------------------------------------------
# Grammar modules (just verify they are importable with correct constants)
# ---------------------------------------------------------------------------


class TestGrammarModules:
    """Smoke tests for grammar module constants."""

    def test_python_grammar(self) -> None:
        from driftscope.ast_engine.grammars.python import GRAMMAR_NAME, LANGUAGE_ID
        assert GRAMMAR_NAME == "python"
        assert LANGUAGE_ID == "python"

    def test_typescript_grammar(self) -> None:
        from driftscope.ast_engine.grammars.typescript import GRAMMAR_NAME, LANGUAGE_ID
        assert GRAMMAR_NAME == "typescript"
        assert LANGUAGE_ID == "typescript"

    def test_go_grammar(self) -> None:
        from driftscope.ast_engine.grammars.go import GRAMMAR_NAME, LANGUAGE_ID
        assert GRAMMAR_NAME == "go"
        assert LANGUAGE_ID == "go"

    def test_java_grammar(self) -> None:
        from driftscope.ast_engine.grammars.java import GRAMMAR_NAME, LANGUAGE_ID
        assert GRAMMAR_NAME == "java"
        assert LANGUAGE_ID == "java"

    def test_ruby_grammar(self) -> None:
        from driftscope.ast_engine.grammars.ruby import GRAMMAR_NAME, LANGUAGE_ID
        assert GRAMMAR_NAME == "ruby"
        assert LANGUAGE_ID == "ruby"
