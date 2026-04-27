"""Tests for driftscope.reporting.csv_export.

Covers: header columns, row count (one per module per window),
data accuracy, empty modules, single module, and edge cases.
"""

from __future__ import annotations

import csv
import io

import pytest

from driftscope.reporting.csv_export import render_csv
from tests.reporting.conftest import _make_result


class TestRenderCsv:
    """Tests for render_csv()."""

    def test_produces_valid_csv(self) -> None:
        """Output is parseable CSV."""
        result = _make_result()
        output = render_csv(result)
        reader = csv.reader(io.StringIO(output))
        rows = list(reader)
        assert len(rows) > 1  # header + data

    def test_has_14_columns(self) -> None:
        """Header row has exactly 14 columns."""
        result = _make_result()
        output = render_csv(result)
        reader = csv.reader(io.StringIO(output))
        header = next(reader)
        assert len(header) == 14

    def test_header_names(self) -> None:
        """Header contains expected column names."""
        result = _make_result()
        output = render_csv(result)
        reader = csv.reader(io.StringIO(output))
        header = next(reader)
        assert header[0] == "module"
        assert header[1] == "window"
        assert header[4] == "ai_survival_rate"
        assert header[13] == "ai_churn_attribution_pct"

    def test_row_count_matches_windows(self) -> None:
        """One row per module per survival window.

        auth.py has 2 windows (30d, 90d), engine.py has 1 window (30d) = 3 rows.
        """
        result = _make_result()
        output = render_csv(result)
        reader = csv.reader(io.StringIO(output))
        rows = list(reader)
        # header + 3 data rows
        assert len(rows) == 4

    def test_data_accuracy(self) -> None:
        """Values in CSV match the source MetricsResult."""
        result = _make_result()
        output = render_csv(result)
        reader = csv.DictReader(io.StringIO(output))
        rows = list(reader)
        auth_30d = [r for r in rows if r["module"] == "src/api/auth.py" and r["window"] == "30d"][0]
        assert auth_30d["ai_lines_introduced"] == "200"
        assert auth_30d["ai_lines_surviving"] == "180"
        assert float(auth_30d["ai_survival_rate"]) == pytest.approx(0.9)
        assert auth_30d["cyclomatic_delta_ai"] == "2.5"
        assert auth_30d["total_churn_lines"] == "120"
        assert float(auth_30d["ai_churn_attribution_pct"]) == pytest.approx(37.5)

    def test_empty_modules_produces_header_only(self) -> None:
        """Empty modules produce CSV with header but no data rows."""
        result = _make_result(empty_modules=True)
        output = render_csv(result)
        reader = csv.reader(io.StringIO(output))
        rows = list(reader)
        assert len(rows) == 1  # header only

    def test_single_module_single_window(self) -> None:
        """Module with one survival window produces one data row."""
        result = _make_result()
        output = render_csv(result)
        reader = csv.DictReader(io.StringIO(output))
        engine_rows = [r for r in reader if r["module"] == "src/core/engine.py"]
        assert len(engine_rows) == 1
        assert engine_rows[0]["window"] == "30d"
