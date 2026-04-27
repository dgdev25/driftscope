"""Pydantic config model for .driftscope.yaml."""

import re

from pydantic import BaseModel, Field, field_validator


class AuthorshipConfig(BaseModel):
    builtin_patterns: bool = True
    custom_patterns: list[str] = Field(default_factory=list)

    @field_validator("custom_patterns")
    @classmethod
    def validate_custom_patterns(cls, v: list[str]) -> list[str]:
        for pattern in v:
            try:
                re.compile(pattern)
            except re.error as e:
                raise ValueError(f"Invalid regex pattern '{pattern}': {e}") from e
        return v


class AnalysisConfig(BaseModel):
    languages: list[str] = Field(
        default_factory=lambda: ["python", "typescript", "javascript", "go", "java", "ruby"]
    )
    exclude_paths: list[str] = Field(
        default_factory=lambda: ["vendor/**", "**/*.generated.*", "node_modules/**"]
    )
    parse_timeout_seconds: float = Field(default=5.0, gt=0.0)
    min_lines_per_module: int = Field(default=10, ge=1)

    @field_validator("languages")
    @classmethod
    def validate_languages(cls, v: list[str]) -> list[str]:
        supported = {"python", "typescript", "javascript", "go", "java", "ruby"}
        invalid = set(v) - supported
        if invalid:
            raise ValueError(
                f"Unsupported languages: {sorted(invalid)}. Supported: {sorted(supported)}"
            )
        return v


class MetricsConfig(BaseModel):
    survival_windows: list[str] = Field(
        default_factory=lambda: ["30d", "90d", "180d", "365d"]
    )
    complexity_metrics: list[str] = Field(
        default_factory=lambda: ["cyclomatic", "cognitive"]
    )

    @field_validator("survival_windows")
    @classmethod
    def validate_survival_windows(cls, v: list[str]) -> list[str]:
        for w in v:
            if not re.match(r"^\d+d$", w):
                raise ValueError(
                    f"Invalid survival window '{w}'. Expected format like '30d', '90d'."
                )
        return v

    @field_validator("complexity_metrics")
    @classmethod
    def validate_complexity_metrics(cls, v: list[str]) -> list[str]:
        supported = {"cyclomatic", "cognitive"}
        invalid = set(v) - supported
        if invalid:
            raise ValueError(
                f"Unsupported complexity metrics: {sorted(invalid)}. Supported: {sorted(supported)}"
            )
        return v


class ThresholdsConfig(BaseModel):
    enforce: bool = False
    ai_churn_attribution_pct: float | None = Field(default=None, ge=0.0, le=100.0)
    ai_survival_rate_pct: float | None = Field(default=None, ge=0.0, le=100.0)


class OutputConfig(BaseModel):
    default_format: str = "markdown"

    @field_validator("default_format")
    @classmethod
    def validate_default_format(cls, v: str) -> str:
        supported = {"json", "markdown", "html", "csv"}
        if v not in supported:
            raise ValueError(f"Unsupported format '{v}'. Supported: {sorted(supported)}")
        return v


class NotificationsConfig(BaseModel):
    slack_webhook: str | None = None

    @field_validator("slack_webhook")
    @classmethod
    def validate_slack_webhook(cls, v: str | None) -> str | None:
        if v is not None and not v.startswith("https://hooks.slack.com/"):
            raise ValueError(
                "Invalid Slack webhook URL. Must start with 'https://hooks.slack.com/'."
            )
        return v


class DriftScopeConfig(BaseModel):
    authorship: AuthorshipConfig = Field(default_factory=AuthorshipConfig)
    analysis: AnalysisConfig = Field(default_factory=AnalysisConfig)
    metrics: MetricsConfig = Field(default_factory=MetricsConfig)
    thresholds: ThresholdsConfig = Field(default_factory=ThresholdsConfig)
    output: OutputConfig = Field(default_factory=OutputConfig)
    notifications: NotificationsConfig = Field(default_factory=NotificationsConfig)
