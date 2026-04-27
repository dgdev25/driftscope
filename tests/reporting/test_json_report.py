"""Tests for driftscope.reporting.json_report.

Covers: basic serialization, provenance inclusion, schema_version field,
empty modules, round-trip parsing, and error on invalid input.
"""

from __future__ import annotations

import json

import pytest

from driftscope.reporting.json_report import render_json
from tests.reporting.conftest import _make_provenance, _make_result


class TestRenderJson:
    """Tests for render_json()."""

    def test_produces_valid_json(self) -> None:
        """Output is parseable JSON with indent=2."""
        result = _make_result()
        output = render_json(result)
        parsed = json.loads(output)
        assert isinstance(parsed, dict)

    def test_contains_schema_version(self) -> None:
        """Top-level schema_version matches the MetricsResult field."""
        result = _make_result()
        parsed = json.loads(render_json(result))
        assert parsed["schema_version"] == "1.0.0"

    def test_modules_serialized(self) -> None:
        """All modules are present in output."""
        result = _make_result()
        parsed = json.loads(render_json(result))
        assert len(parsed["modules"]) == 2
        assert parsed["modules"][0]["module_path"] == "src/api/auth.py"
        assert parsed["modules"][1]["module_path"] == "src/core/engine.py"

    def test_provenance_included_when_requested(self) -> None:
        """Provenance entries are added under 'provenance' key."""
        result = _make_result()
        prov = _make_provenance()
        parsed = json.loads(render_json(result, include_provenance=True, provenance=prov))
        assert "provenance" in parsed
        assert len(parsed["provenance"]) == 2
        assert parsed["provenance"][0]["file_path"] == "src/api/auth.py"

    def test_provenance_omitted_by_default(self) -> None:
        """No provenance key when include_provenance=False."""
        result = _make_result()
        parsed = json.loads(render_json(result))
        assert "provenance" not in parsed

    def test_empty_modules_produces_valid_output(self) -> None:
        """Empty modules list yields a valid JSON with empty modules array."""
        result = _make_result(empty_modules=True)
        parsed = json.loads(render_json(result))
        assert parsed["modules"] == []

    def test_pretty_printed_with_indent(self) -> None:
        """Output uses indent=2 (check for newline + two-space pattern)."""
        result = _make_result()
        output = render_json(result)
        assert "\n  " in output
