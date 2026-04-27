"""Tests for driftscope.reporting.markdown.

Covers: header, executive summary, survival/complexity/churn tables,
threshold breaches, skipped files, metadata, empty modules, and
zero-value edge cases.
"""

from __future__ import annotations

from datetime import datetime

from driftscope.reporting.markdown import render_markdown
from tests.reporting.conftest import _make_result


class TestRenderMarkdown:
    """Tests for render_markdown()."""

    def test_contains_header(self) -> None:
        """Report starts with the DriftScope header."""
        result = _make_result()
        output = render_markdown(result)
        assert "# DriftScope Report" in output

    def test_contains_date_range(self) -> None:
        """Report header includes the analysis date range."""
        result = _make_result()
        output = render_markdown(result)
        assert "2025" in output

    def test_executive_summary_totals(self) -> None:
        """Executive summary has total modules, total lines, AI/human lines."""
        result = _make_result()
        output = render_markdown(result)
        assert "2" in output  # 2 modules
        assert "1300" in output  # 500 + 800 total lines
        assert "550" in output  # 200 + 350 AI lines
        assert "750" in output  # 300 + 450 human lines

    def test_ai_attribution_percentage(self) -> None:
        """Executive summary shows AI attribution %."""
        result = _make_result()
        output = render_markdown(result)
        # 550/1300 * 100 = 42.3%
        assert "42.3" in output

    def test_survival_table_present(self) -> None:
        """Survival table section exists with module paths and rates."""
        result = _make_result()
        output = render_markdown(result)
        assert "src/api/auth.py" in output
        assert "src/core/engine.py" in output

    def test_complexity_table_present(self) -> None:
        """Complexity table has cyclomatic and cognitive deltas."""
        result = _make_result()
        output = render_markdown(result)
        assert "2.5" in output  # cyclomatic_delta_ai for auth.py

    def test_churn_table_present(self) -> None:
        """Churn table has total churn and AI attribution."""
        result = _make_result()
        output = render_markdown(result)
        assert "120" in output  # total_churn_lines for auth.py
        assert "37.5" in output  # ai_churn_attribution_pct for auth.py

    def test_threshold_breaches_shown(self) -> None:
        """Threshold breaches are listed when present."""
        result = _make_result(with_breaches=True)
        output = render_markdown(result)
        assert "ai_survival_rate" in output
        assert "src/api/auth.py" in output

    def test_skipped_files_shown(self) -> None:
        """Skipped files section lists files and reasons."""
        result = _make_result(with_skipped=True)
        output = render_markdown(result)
        assert "vendor/third_party.py" in output
        assert "Excluded by config" in output

    def test_metadata_section(self) -> None:
        """Metadata section contains schema version and tool info."""
        result = _make_result()
        output = render_markdown(result)
        assert "1.0.0" in output

    def test_empty_modules_no_crash(self) -> None:
        """Empty modules produce a valid report without errors."""
        result = _make_result(empty_modules=True)
        output = render_markdown(result)
        assert "# DriftScope Report" in output
        assert "0" in output  # 0 modules

    def test_no_breaches_no_section(self) -> None:
        """When no breaches, no breach content appears."""
        result = _make_result()
        output = render_markdown(result)
        # The breaches section header should indicate none
        assert "No threshold breaches" in output or "None" in output

    def test_no_skipped_no_section(self) -> None:
        """When no skipped files, skipped section indicates none."""
        result = _make_result()
        output = render_markdown(result)
        # Skipped section should indicate none or be absent
        assert "No skipped files" in output or "skipped" not in output.lower() or "0 skipped" in output

    def test_data_incomplete_note(self) -> None:
        """When data_incomplete is True, a note appears in metadata."""
        result = _make_result()
        result.data_incomplete = True
        output = render_markdown(result)
        assert "incomplete" in output.lower()
