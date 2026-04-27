"""Provenance model for line-level authorship tracking."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class ProvenanceEntry(BaseModel):
    """Line-level provenance entry for a specific code region."""

    file_path: str
    line_start: int
    line_end: int
    authorship_class: Literal["human", "ai"]
    originating_commit_sha: str
    commit_timestamp: datetime
    co_authorship_tag: str | None = None
