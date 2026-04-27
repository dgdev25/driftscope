"""Tests for AST diff models."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from driftscope.models.ast_diff import ASTDiffSet, ASTFileDiff, ASTNodeChange


def test_ast_node_change_added() -> None:
    change = ASTNodeChange(
        node_type="function_definition",
        start_line=10,
        end_line=25,
        change_type="added",
        text_hash="a" * 64,
    )
    assert change.change_type == "added"


def test_ast_node_change_rejects_invalid_hash() -> None:
    with pytest.raises(ValidationError):
        ASTNodeChange(
            node_type="function_definition",
            start_line=10,
            end_line=25,
            change_type="added",
            text_hash="tooshort",
        )


def test_ast_node_change_rejects_invalid_change_type() -> None:
    with pytest.raises(ValidationError):
        ASTNodeChange(
            node_type="function_definition",
            start_line=10,
            end_line=25,
            change_type="renamed",
            text_hash="a" * 64,
        )


def test_ast_file_diff_new_file() -> None:
    diff = ASTFileDiff(
        file_path=Path("src/new_module.py"),
        commit_sha="a" * 40,
        before_hash=None,
        after_hash="b" * 64,
        changes=[],
        authorship_class="ai",
    )
    assert diff.before_hash is None


def test_ast_diff_set() -> None:
    ds = ASTDiffSet(
        diffs=[],
        skipped_files=[{"path": "vendor/lib.js", "reason": "unsupported_extension"}],
    )
    assert len(ds.skipped_files) == 1
