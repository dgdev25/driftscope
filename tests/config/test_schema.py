"""Tests for the DriftScopeConfig Pydantic schema."""

import pytest
from pydantic import ValidationError

from driftscope.config.schema import (
    AnalysisConfig,
    AuthorshipConfig,
    DriftScopeConfig,
    MetricsConfig,
    NotificationsConfig,
    OutputConfig,
    ThresholdsConfig,
)


def test_default_config() -> None:
    config = DriftScopeConfig()
    assert config.authorship.builtin_patterns is True
    assert config.analysis.languages == [
        "python",
        "typescript",
        "javascript",
        "go",
        "java",
        "ruby",
    ]
    assert config.metrics.survival_windows == ["30d", "90d", "180d", "365d"]
    assert config.thresholds.enforce is False
    assert config.output.default_format == "markdown"
    assert config.notifications.slack_webhook is None


def test_authorship_custom_patterns_valid() -> None:
    config = AuthorshipConfig(
        custom_patterns=[r"AI-Generated:\s*\w+", r"Co-Authored-By:\s*.*Bot"]
    )
    assert len(config.custom_patterns) == 2


def test_authorship_custom_patterns_invalid_regex() -> None:
    with pytest.raises(ValidationError, match="Invalid regex"):
        AuthorshipConfig(custom_patterns=["[unclosed"])


def test_analysis_unsupported_language() -> None:
    with pytest.raises(ValidationError, match="Unsupported languages"):
        AnalysisConfig(languages=["python", "fortran"])


def test_analysis_min_lines_must_be_positive() -> None:
    with pytest.raises(ValidationError):
        AnalysisConfig(min_lines_per_module=0)


def test_metrics_invalid_window_format() -> None:
    with pytest.raises(ValidationError, match="Invalid survival window"):
        MetricsConfig(survival_windows=["3months"])


def test_metrics_valid_complexity_metrics() -> None:
    config = MetricsConfig(complexity_metrics=["cyclomatic", "cognitive"])
    assert config.complexity_metrics == ["cyclomatic", "cognitive"]


def test_metrics_unsupported_complexity_metric() -> None:
    with pytest.raises(ValidationError, match="Unsupported complexity metrics"):
        MetricsConfig(complexity_metrics=["cyclomatic", "halstead"])


def test_thresholds_valid() -> None:
    config = ThresholdsConfig(
        enforce=True,
        ai_churn_attribution_pct=50.0,
        ai_survival_rate_pct=60.0,
    )
    assert config.enforce is True
    assert config.ai_churn_attribution_pct == 50.0


def test_thresholds_null_means_disabled() -> None:
    config = ThresholdsConfig()
    assert config.ai_churn_attribution_pct is None
    assert config.ai_survival_rate_pct is None


def test_thresholds_rejects_over_100() -> None:
    with pytest.raises(ValidationError):
        ThresholdsConfig(ai_churn_attribution_pct=150.0)


def test_output_supported_formats() -> None:
    for fmt in ("json", "markdown", "html", "csv"):
        config = OutputConfig(default_format=fmt)
        assert config.default_format == fmt


def test_output_unsupported_format() -> None:
    with pytest.raises(ValidationError, match="Unsupported format"):
        OutputConfig(default_format="pdf")


def test_notifications_valid_slack_webhook() -> None:
    config = NotificationsConfig(
        slack_webhook="https://hooks.slack.com/services/T00/B00/xxx"
    )
    assert config.slack_webhook is not None


def test_notifications_invalid_slack_webhook() -> None:
    with pytest.raises(ValidationError, match="Invalid Slack webhook"):
        NotificationsConfig(slack_webhook="https://example.com/webhook")


def test_full_config_from_dict() -> None:
    config = DriftScopeConfig(
        authorship={"builtin_patterns": False, "custom_patterns": [r"AI:\s*\w+"]},
        analysis={"languages": ["python"], "parse_timeout_seconds": 10.0},
        metrics={"survival_windows": ["90d"]},
        thresholds={"enforce": True, "ai_churn_attribution_pct": 50.0},
        output={"default_format": "json"},
    )
    assert config.authorship.builtin_patterns is False
    assert config.analysis.parse_timeout_seconds == 10.0
    assert config.thresholds.enforce is True
