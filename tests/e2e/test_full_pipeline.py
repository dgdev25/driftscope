"""E2E: Full pipeline execution produces valid reports."""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from driftscope.cli.app import app

runner = CliRunner()


class TestFullPipeline:
    """E2E tests running the full analyze pipeline against a fixture repo."""

    def test_analyze_json_output(self, fixture_repo: Path) -> None:
        """analyze --format json produces valid JSON with expected structure."""
        result = runner.invoke(
            app,
            ["analyze", "--repo-path", str(fixture_repo), "--format", "json", "--output", "-"],
        )
        assert result.exit_code == 0, result.output
        data = json.loads(result.stdout)
        assert "modules" in data
        assert "commit_range" in data
        assert "schema_version" in data

    def test_analyze_markdown_output(self, fixture_repo: Path) -> None:
        """analyze --format markdown produces valid markdown."""
        result = runner.invoke(
            app,
            ["analyze", "--repo-path", str(fixture_repo), "--format", "markdown", "--output", "-"],
        )
        assert result.exit_code == 0, result.output
        assert "# DriftScope Report" in result.stdout

    def test_analyze_html_output(self, fixture_repo: Path) -> None:
        """analyze --format html produces valid HTML."""
        result = runner.invoke(
            app,
            ["analyze", "--repo-path", str(fixture_repo), "--format", "html", "--output", "-"],
        )
        assert result.exit_code == 0, result.output
        assert "<html" in result.stdout.lower()
        assert "DriftScope" in result.stdout

    def test_analyze_csv_output(self, fixture_repo: Path) -> None:
        """analyze --format csv produces valid CSV with headers."""
        result = runner.invoke(
            app,
            ["analyze", "--repo-path", str(fixture_repo), "--format", "csv", "--output", "-"],
        )
        assert result.exit_code == 0, result.output
        lines = result.stdout.strip().split("\n")
        assert len(lines) >= 1
        assert "module" in lines[0].lower()

    def test_analyze_with_since_filter(self, fixture_repo: Path) -> None:
        """analyze --since filters commits to the specified date range."""
        # Full range
        full = runner.invoke(
            app,
            ["analyze", "--repo-path", str(fixture_repo), "--format", "json", "--output", "-"],
        )
        assert full.exit_code == 0
        full_data = json.loads(full.stdout)

        # Narrow range (only commits from May+)
        narrow = runner.invoke(
            app,
            [
                "analyze",
                "--repo-path", str(fixture_repo),
                "--since", "2024-05-01",
                "--format", "json",
                "--output", "-",
            ],
        )
        assert narrow.exit_code == 0
        narrow_data = json.loads(narrow.stdout)

        # Narrow range should have fewer or equal commits
        assert len(narrow_data.get("modules", [])) <= len(full_data.get("modules", []))

    def test_analyze_writes_to_file(self, fixture_repo: Path, tmp_path: Path) -> None:
        """analyze with --output <file> writes the report to disk."""
        output_file = tmp_path / "report.json"
        result = runner.invoke(
            app,
            [
                "analyze",
                "--repo-path", str(fixture_repo),
                "--format", "json",
                "--output", str(output_file),
            ],
        )
        assert result.exit_code == 0, result.output
        assert output_file.is_file()
        content = output_file.read_text(encoding="utf-8")
        json.loads(content)  # Valid JSON
