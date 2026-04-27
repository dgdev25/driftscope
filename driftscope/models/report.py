"""Top-level report model — the output contract."""

from datetime import datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from driftscope.models.metrics import ModuleMetrics


class ThresholdBreach(BaseModel):
    """A metric value that crossed a configured threshold."""

    metric: str
    module_path: str
    value: float
    threshold: float
    direction: Literal["above", "below"]


class MetricsResult(BaseModel):
    """Top-level analysis result — the root of all report outputs."""

    repo_path: Path
    commit_range: tuple[str, str]
    range_start: datetime
    range_end: datetime
    schema_version: str = "1.0.0"
    modules: list[ModuleMetrics]
    skipped_files: list[dict[str, str]]
    data_incomplete: bool = False
    threshold_breaches: list[ThresholdBreach] = Field(default_factory=list)
