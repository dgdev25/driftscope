"""Tests for driftscope.reporting.html.

Covers: valid HTML structure, inline CSS, responsive design,
all report sections, color coding, empty modules, edge cases.
"""

from __future__ import annotations

import re

from driftscope.reporting.html import render_html
from tests.reporting.conftest import _make_result


class TestRenderHtml:
    """Tests for render_html()."""

    def test_produces_valid_html(self) -> None:
        """Output has <html>, <head>, <body> tags."""
        result = _make_result()
        output = render_html(result)
        assert "<html" in output
        assert "</html>" in output
        assert "<head>" in output
        assert "</head>" in output
        assert "<body>" in output
        assert "</body>" in output

    def test_contains_inline_css(self) -> None:
        """CSS is inlined in <style> tags, not external."""
        result = _make_result()
        output = render_html(result)
        assert "<style>" in output
        assert "</style>" in output
        assert 'href="' not in output.split("</style>")[0].split("<style>")[0]
        assert "link" not in output.split("<style>")[0].lower() or "stylesheet" not in output

    def test_no_javascript(self) -> None:
        """No <script> tags in output."""
        result = _make_result()
        output = render_html(result)
        assert "<script" not in output.lower()
        assert "javascript" not in output.lower()

    def test_responsive_design(self) -> None:
        """Contains viewport meta tag for responsive design."""
        result = _make_result()
        output = render_html(result)
        assert "viewport" in output
        assert "max-width" in output

    def test_contains_header(self) -> None:
        """Report has DriftScope heading."""
        result = _make_result()
        output = render_html(result)
        assert "DriftScope" in output

    def test_contains_date_range(self) -> None:
        """Report shows the analysis date range."""
        result = _make_result()
        output = render_html(result)
        assert "2025" in output

    def test_executive_summary_present(self) -> None:
        """Executive summary section with totals."""
        result = _make_result()
        output = render_html(result)
        assert "1,300" in output  # total lines (comma-formatted)

    def test_survival_table_present(self) -> None:
        """Survival data rendered in an HTML table."""
        result = _make_result()
        output = render_html(result)
        assert "<table" in output
        assert "src/api/auth.py" in output

    def test_complexity_table_present(self) -> None:
        """Complexity deltas in a table."""
        result = _make_result()
        output = render_html(result)
        assert "2.5" in output  # cyclomatic_delta_ai

    def test_churn_table_present(self) -> None:
        """Churn data in a table."""
        result = _make_result()
        output = render_html(result)
        assert "120" in output  # total_churn_lines

    def test_threshold_breach_color_coding(self) -> None:
        """Breach rows have a CSS class or style indicating alert."""
        result = _make_result(with_breaches=True)
        output = render_html(result)
        assert "breach" in output.lower() or "alert" in output.lower() or "danger" in output.lower() or "warning" in output.lower()

    def test_threshold_breach_shows_details(self) -> None:
        """Breach details (metric, module, value) are visible."""
        result = _make_result(with_breaches=True)
        output = render_html(result)
        assert "ai_survival_rate" in output
        assert "0.75" in output
        assert "0.8" in output  # threshold

    def test_skipped_files_present(self) -> None:
        """Skipped files section lists files."""
        result = _make_result(with_skipped=True)
        output = render_html(result)
        assert "vendor/third_party.py" in output
        assert "Excluded by config" in output

    def test_empty_modules_no_crash(self) -> None:
        """Empty modules produce valid HTML."""
        result = _make_result(empty_modules=True)
        output = render_html(result)
        assert "<html" in output
        assert "0" in output

    def test_self_contained_no_external_resources(self) -> None:
        """No external CDN or resource references."""
        result = _make_result()
        output = render_html(result)
        assert "cdn" not in output.lower()
        assert "http://" not in output
        assert "https://" not in output

    def test_data_incomplete_note(self) -> None:
        """When data_incomplete is True, a warning note appears in metadata."""
        result = _make_result()
        result.data_incomplete = True
        output = render_html(result)
        assert "incomplete" in output.lower()
