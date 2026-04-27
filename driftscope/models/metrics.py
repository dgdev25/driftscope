"""Metrics computation models — survival, complexity, churn."""

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field


class SurvivalMetrics(BaseModel):
    """Line survival rate for a specific time window."""

    window: str = Field(pattern=r"^\d+d$")
    ai_lines_introduced: int = Field(ge=0)
    ai_lines_surviving: int = Field(ge=0)
    ai_survival_rate: float = Field(ge=0.0, le=1.0)
    human_lines_introduced: int = Field(ge=0)
    human_lines_surviving: int = Field(ge=0)
    human_survival_rate: float = Field(ge=0.0, le=1.0)


class WeeklyComplexity(BaseModel):
    """Complexity metrics for a single week."""

    week_start: date
    ai_cyclomatic_mean: float
    human_cyclomatic_mean: float
    ai_cognitive_mean: float
    human_cognitive_mean: float
    ai_commit_count: int = Field(ge=0)
    human_commit_count: int = Field(ge=0)


class ComplexityMetrics(BaseModel):
    """Complexity delta metrics segmented by authorship."""

    cyclomatic_delta_ai: float
    cyclomatic_delta_human: float
    cognitive_delta_ai: float
    cognitive_delta_human: float
    weekly_series: list[WeeklyComplexity]


class ChurnMetrics(BaseModel):
    """Module-level churn attribution over a rolling 365-day window."""

    total_churn_lines: int = Field(ge=0)
    ai_churn_lines: int = Field(ge=0)
    ai_churn_attribution_pct: float = Field(ge=0.0, le=100.0)


class ModuleMetrics(BaseModel):
    """Aggregated metrics for a single repository module."""

    module_path: str
    total_lines: int = Field(ge=0)
    ai_lines: int = Field(ge=0)
    human_lines: int = Field(ge=0)
    survival: dict[str, SurvivalMetrics]
    complexity: ComplexityMetrics
    churn: ChurnMetrics
