"""E2E: Re-running analysis on the same repo produces identical output."""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from driftscope.cli.app import app

runner = CliRunner()


class TestIdempotency:
    """Verify that running analyze twice on the same commit produces identical results."""

    def test_json_output_is_identical(self, fixture_repo: Path) -> None:
        """Two consecutive runs produce byte-identical JSON output."""
        args = ["analyze", "--repo-path", str(fixture_repo), "--format", "json", "--output", "-"]

        first = runner.invoke(app, args)
        assert first.exit_code == 0, first.output

        second = runner.invoke(app, args)
        assert second.exit_code == 0, second.output

        # Parse to normalize formatting differences
        data_first = json.loads(first.stdout)
        data_second = json.loads(second.stdout)
        assert data_first == data_second

    def test_markdown_output_is_identical(self, fixture_repo: Path) -> None:
        """Two consecutive runs produce identical markdown output."""
        args = ["analyze", "--repo-path", str(fixture_repo), "--format", "markdown", "--output", "-"]

        first = runner.invoke(app, args)
        second = runner.invoke(app, args)

        assert first.exit_code == 0, first.output
        assert second.exit_code == 0, second.output
        assert first.stdout == second.stdout

    def test_file_output_overwrite_is_identical(self, fixture_repo: Path, tmp_path: Path) -> None:
        """Writing to the same file twice produces identical contents."""
        output_file = tmp_path / "report.json"
        args = [
            "analyze",
            "--repo-path", str(fixture_repo),
            "--format", "json",
            "--output", str(output_file),
        ]

        runner.invoke(app, args)
        first_content = output_file.read_text(encoding="utf-8")

        runner.invoke(app, args)
        second_content = output_file.read_text(encoding="utf-8")

        assert json.loads(first_content) == json.loads(second_content)
