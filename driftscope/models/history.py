"""Commit history and attributed history models."""

from datetime import datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from driftscope.models.blame import BlameLine
from driftscope.models.commit import Commit


class CommitHistory(BaseModel):
    """Ordered collection of commits with blame data for a repository."""

    repo_path: Path
    commits: list[Commit]
    blame: dict[Path, list[BlameLine]]
    range_start: datetime
    range_end: datetime


class AttributedCommit(Commit):
    """A commit with authorship classification applied."""

    authorship_class: Literal["human", "ai"]
    matched_pattern: str | None = None
    matched_text: str | None = None


class AttributedHistory(BaseModel):
    """Commit history with authorship attribution applied."""

    repo_path: Path
    commits: list[AttributedCommit]
    blame: dict[Path, list[BlameLine]]
    range_start: datetime
    range_end: datetime
    ai_commit_count: int = Field(ge=0)
    human_commit_count: int = Field(ge=0)
