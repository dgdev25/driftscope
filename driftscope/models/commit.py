"""Git commit data model."""

from datetime import datetime

from pydantic import BaseModel, Field


class Commit(BaseModel):
    """A single git commit with full metadata."""

    sha: str = Field(min_length=40, max_length=40, pattern=r"^[0-9a-f]{40}$")
    short_sha: str = Field(min_length=7, max_length=7, pattern=r"^[0-9a-f]{7}$")
    timestamp: datetime
    author_name: str
    author_email: str
    committer_name: str
    committer_email: str
    message_subject: str
    message_body: str
    parent_shas: list[str]

    model_config = {"frozen": True}
