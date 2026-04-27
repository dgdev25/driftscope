"""Tests for the MetricsResult report model."""

from datetime import datetime, timezone
from pathlib import Path

from driftscope.models.report import MetricsResult, ThresholdBreach
from driftscope.models.metrics import (
    ChurnMetrics,
    ComplexityMetrics,
    ModuleMetrics,
    SurvivalMetrics,
)


def _module_metrics() -> ModuleMetrics:
    return ModuleMetrics(
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


def test_metrics_result_valid() -> None:
    result = MetricsResult(
        repo_path=Path("/tmp/repo"),
        commit_range=("a" * 40, "c" * 40),
        range_start=datetime(2025, 1, 1, tzinfo=timezone.utc),
        range_end=datetime(2025, 4, 1, tzinfo=timezone.utc),
        modules=[_module_metrics()],
        skipped_files=[],
    )
    assert result.schema_version == "1.0.0"
    assert len(result.modules) == 1
    assert result.threshold_breaches == []


def test_metrics_result_with_breaches() -> None:
    result = MetricsResult(
        repo_path=Path("/tmp/repo"),
        commit_range=("a" * 40, "c" * 40),
        range_start=datetime(2025, 1, 1, tzinfo=timezone.utc),
        range_end=datetime(2025, 4, 1, tzinfo=timezone.utc),
        modules=[_module_metrics()],
        skipped_files=[],
        threshold_breaches=[ThresholdBreach(
            metric="ai_churn_attribution_pct",
            module_path="src/payments",
            value=62.5,
            threshold=50.0,
            direction="above",
        )],
    )
    assert len(result.threshold_breaches) == 1
    assert result.threshold_breaches[0].direction == "above"


def test_metrics_result_json_round_trip() -> None:
    result = MetricsResult(
        repo_path=Path("/tmp/repo"),
        commit_range=("a" * 40, "c" * 40),
        range_start=datetime(2025, 1, 1, tzinfo=timezone.utc),
        range_end=datetime(2025, 4, 1, tzinfo=timezone.utc),
        modules=[_module_metrics()],
        skipped_files=[],
        data_incomplete=True,
    )
    json_str = result.model_dump_json()
    restored = MetricsResult.model_validate_json(json_str)
    assert restored.schema_version == result.schema_version
    assert restored.data_incomplete is True
    assert len(restored.modules) == 1
