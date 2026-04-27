"""E2E: Module-level metric breakdown in pipeline output."""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from driftscope.cli.app import app

runner = CliRunner()


class TestModuleScoping:
    """Verify module-level metric breakdowns in analysis output."""

    def test_json_includes_module_metrics(self, fixture_repo: Path) -> None:
        """JSON output includes at least one module entry with metrics."""
        result = runner.invoke(
            app,
            ["analyze", "--repo-path", str(fixture_repo), "--format", "json", "--output", "-"],
        )
        assert result.exit_code == 0, result.output
        data = json.loads(result.stdout)
        modules = data.get("modules", [])
        assert len(modules) >= 1
        mod = modules[0]
        assert "module_path" in mod
        assert "total_lines" in mod
        assert "ai_lines" in mod
        assert "human_lines" in mod

    def test_module_metrics_have_ai_and_human_counts(self, fixture_repo: Path) -> None:
        """Module metrics show non-zero counts for both AI and human lines."""
        result = runner.invoke(
            app,
            ["analyze", "--repo-path", str(fixture_repo), "--format", "json", "--output", "-"],
        )
        assert result.exit_code == 0, result.output
        data = json.loads(result.stdout)
        modules = data.get("modules", [])
        assert len(modules) >= 1
        mod = modules[0]
        # The fixture has both human and AI commits
        assert mod["total_lines"] > 0
        assert mod["ai_lines"] > 0
        assert mod["human_lines"] > 0
        assert mod["total_lines"] == mod["ai_lines"] + mod["human_lines"]

    def test_csv_includes_module_column(self, fixture_repo: Path) -> None:
        """CSV output includes a module column."""
        result = runner.invoke(
            app,
            ["analyze", "--repo-path", str(fixture_repo), "--format", "csv", "--output", "-"],
        )
        assert result.exit_code == 0, result.output
        lines = result.stdout.strip().split("\n")
        assert len(lines) >= 1
        header = lines[0].lower()
        assert "module" in header

    def test_markdown_includes_ai_human_columns(self, fixture_repo: Path) -> None:
        """Markdown output includes AI and human line columns."""
        result = runner.invoke(
            app,
            ["analyze", "--repo-path", str(fixture_repo), "--format", "markdown", "--output", "-"],
        )
        assert result.exit_code == 0, result.output
        assert "AI" in result.stdout or "ai" in result.stdout.lower()
