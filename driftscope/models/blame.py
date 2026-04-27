"""Git blame line data model."""

from pydantic import BaseModel, Field


class BlameLine(BaseModel):
    """A single line from git blame output."""

    line_number: int = Field(ge=1)
    commit_sha: str = Field(min_length=40, max_length=40, pattern=r"^[0-9a-f]{40}$")
    author_name: str
    author_email: str
    content: str

    model_config = {"frozen": True}
