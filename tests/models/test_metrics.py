"""Tests for metrics models."""

from datetime import date

import pytest
from pydantic import ValidationError

from driftscope.models.metrics import (
    ChurnMetrics,
    ComplexityMetrics,
    ModuleMetrics,
    SurvivalMetrics,
    WeeklyComplexity,
)


def test_survival_metrics_valid() -> None:
    sm = SurvivalMetrics(
        window="90d",
        ai_lines_introduced=100,
        ai_lines_surviving=67,
        ai_survival_rate=0.67,
        human_lines_introduced=500,
        human_lines_surviving=450,
        human_survival_rate=0.9,
    )
    assert sm.ai_survival_rate == 0.67


def test_survival_metrics_rejects_rate_above_one() -> None:
    with pytest.raises(ValidationError):
        SurvivalMetrics(
            window="90d",
            ai_lines_introduced=100,
            ai_lines_surviving=100,
            ai_survival_rate=1.5,
            human_lines_introduced=100,
            human_lines_surviving=100,
            human_survival_rate=1.0,
        )


def test_survival_metrics_rejects_invalid_window() -> None:
    with pytest.raises(ValidationError):
        SurvivalMetrics(
            window="3months",
            ai_lines_introduced=100,
            ai_lines_surviving=67,
            ai_survival_rate=0.67,
            human_lines_introduced=100,
            human_lines_surviving=100,
            human_survival_rate=1.0,
        )


def test_weekly_complexity_valid() -> None:
    wc = WeeklyComplexity(
        week_start=date(2025, 11, 3),
        ai_cyclomatic_mean=2.3,
        human_cyclomatic_mean=0.8,
        ai_cognitive_mean=3.1,
        human_cognitive_mean=1.2,
        ai_commit_count=12,
        human_commit_count=34,
    )
    assert wc.ai_commit_count == 12


def test_churn_metrics_valid() -> None:
    cm = ChurnMetrics(
        total_churn_lines=1000,
        ai_churn_lines=425,
        ai_churn_attribution_pct=42.5,
    )
    assert cm.ai_churn_attribution_pct == 42.5


def test_churn_metrics_rejects_pct_over_100() -> None:
    with pytest.raises(ValidationError):
        ChurnMetrics(
            total_churn_lines=100,
            ai_churn_lines=150,
            ai_churn_attribution_pct=150.0,
        )


def test_module_metrics_valid() -> None:
    mm = ModuleMetrics(
        module_path="src/payments",
        total_lines=5000,
        ai_lines=1204,
        human_lines=3796,
        survival={"90d": SurvivalMetrics(
            window="90d",
            ai_lines_introduced=100,
            ai_lines_surviving=67,
            ai_survival_rate=0.67,
            human_lines_introduced=500,
            human_lines_surviving=450,
            human_survival_rate=0.9,
        )},
        complexity=ComplexityMetrics(
            cyclomatic_delta_ai=3.2,
            cyclomatic_delta_human=1.1,
            cognitive_delta_ai=4.5,
            cognitive_delta_human=2.0,
            weekly_series=[],
        ),
        churn=ChurnMetrics(
            total_churn_lines=2000,
            ai_churn_lines=500,
            ai_churn_attribution_pct=25.0,
        ),
    )
    assert mm.module_path == "src/payments"
