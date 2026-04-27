"""Shared test fixtures for reporting tests.

Provides a _make_result() helper that builds a fully-populated MetricsResult
for deterministic testing of all four renderers.
"""

from __future__ import annotations

from datetime import date, datetime
from pathlib import Path

from driftscope.models.metrics import (
    ChurnMetrics,
    ComplexityMetrics,
    ModuleMetrics,
    SurvivalMetrics,
    WeeklyComplexity,
)
from driftscope.models.provenance import ProvenanceEntry
from driftscope.models.report import MetricsResult, ThresholdBreach


def _make_result(
    *,
    with_breaches: bool = False,
    with_skipped: bool = False,
    empty_modules: bool = False,
) -> MetricsResult:
    """Build a fully-populated MetricsResult for testing.

    Args:
        with_breaches: Include threshold breaches.
        with_skipped: Include skipped files.
        empty_modules: Return a result with no modules.

    Returns:
        A MetricsResult instance with deterministic test data.
    """
    modules: list[ModuleMetrics] = []
    if not empty_modules:
        modules = [
            ModuleMetrics(
                module_path="src/api/auth.py",
                total_lines=500,
                ai_lines=200,
                human_lines=300,
                survival={
                    "30d": SurvivalMetrics(
                        window="30d",
                        ai_lines_introduced=200,
                        ai_lines_surviving=180,
                        ai_survival_rate=0.9,
                        human_lines_introduced=300,
                        human_lines_surviving=285,
                        human_survival_rate=0.95,
                    ),
                    "90d": SurvivalMetrics(
                        window="90d",
                        ai_lines_introduced=200,
                        ai_lines_surviving=150,
                        ai_survival_rate=0.75,
                        human_lines_introduced=300,
                        human_lines_surviving=260,
                        human_survival_rate=0.867,
                    ),
                },
                complexity=ComplexityMetrics(
                    cyclomatic_delta_ai=2.5,
                    cyclomatic_delta_human=1.0,
                    cognitive_delta_ai=3.0,
                    cognitive_delta_human=0.8,
                    weekly_series=[
                        WeeklyComplexity(
                            week_start=date(2025, 1, 6),
                            ai_cyclomatic_mean=5.0,
                            human_cyclomatic_mean=3.0,
                            ai_cognitive_mean=6.0,
                            human_cognitive_mean=2.5,
                            ai_commit_count=10,
                            human_commit_count=15,
                        ),
                    ],
                ),
                churn=ChurnMetrics(
                    total_churn_lines=120,
                    ai_churn_lines=45,
                    ai_churn_attribution_pct=37.5,
                ),
            ),
            ModuleMetrics(
                module_path="src/core/engine.py",
                total_lines=800,
                ai_lines=350,
                human_lines=450,
                survival={
                    "30d": SurvivalMetrics(
                        window="30d",
                        ai_lines_introduced=350,
                        ai_lines_surviving=300,
                        ai_survival_rate=0.857,
                        human_lines_introduced=450,
                        human_lines_surviving=430,
                        human_survival_rate=0.956,
                    ),
                },
                complexity=ComplexityMetrics(
                    cyclomatic_delta_ai=1.2,
                    cyclomatic_delta_human=0.5,
                    cognitive_delta_ai=1.8,
                    cognitive_delta_human=0.3,
                    weekly_series=[],
                ),
                churn=ChurnMetrics(
                    total_churn_lines=200,
                    ai_churn_lines=80,
                    ai_churn_attribution_pct=40.0,
                ),
            ),
        ]

    breaches: list[ThresholdBreach] = []
    if with_breaches:
        breaches = [
            ThresholdBreach(
                metric="ai_survival_rate",
                module_path="src/api/auth.py",
                value=0.75,
                threshold=0.8,
                direction="below",
            ),
        ]

    skipped: list[dict[str, str]] = []
    if with_skipped:
        skipped = [
            {"file": "vendor/third_party.py", "reason": "Excluded by config"},
            {"file": "generated/proto.py", "reason": "Binary or generated file"},
        ]

    return MetricsResult(
        repo_path=Path("/repo/project"),
        commit_range=("abc1234", "def5678"),
        range_start=datetime(2025, 1, 1, 0, 0, 0),
        range_end=datetime(2025, 3, 31, 23, 59, 59),
        schema_version="1.0.0",
        modules=modules,
        skipped_files=skipped,
        threshold_breaches=breaches,
    )


def _make_provenance() -> list[ProvenanceEntry]:
    """Build a list of ProvenanceEntry objects for testing."""
    return [
        ProvenanceEntry(
            file_path="src/api/auth.py",
            line_start=10,
            line_end=25,
            authorship_class="ai",
            originating_commit_sha="abc1234",
            commit_timestamp=datetime(2025, 1, 15, 10, 30, 0),
            co_authorship_tag="Claude",
        ),
        ProvenanceEntry(
            file_path="src/core/engine.py",
            line_start=50,
            line_end=70,
            authorship_class="human",
            originating_commit_sha="def5678",
            commit_timestamp=datetime(2025, 2, 20, 14, 0, 0),
        ),
    ]
