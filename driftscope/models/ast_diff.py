"""AST-level diff models for tree-sitter analysis."""

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field


class ASTNodeChange(BaseModel):
    """A single AST node change within a commit."""

    node_type: str
    start_line: int = Field(ge=1)
    end_line: int = Field(ge=1)
    change_type: Literal["added", "removed", "modified"]
    text_hash: str = Field(min_length=64, max_length=64)


class ASTFileDiff(BaseModel):
    """AST diff for a single file within a single commit."""

    file_path: Path
    commit_sha: str = Field(min_length=40, max_length=40)
    before_hash: str | None = None
    after_hash: str | None = None
    changes: list[ASTNodeChange]
    authorship_class: Literal["human", "ai"]


class ASTDiffSet(BaseModel):
    """Collection of AST diffs across all files and commits."""

    diffs: list[ASTFileDiff]
    skipped_files: list[dict[str, str]]
