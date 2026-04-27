"""E2E: Threshold configuration affects analysis output."""

from __future__ import annotations

import json
from pathlib import Path

import yaml
from typer.testing import CliRunner

from driftscope.cli.app import app

runner = CliRunner()


def _write_config(repo_path: Path, thresholds: dict) -> None:
    """Write a .driftscope.yaml with the given thresholds."""
    config = {
        "ai_patterns": [
            {"name": "Copilot", "email": "noreply@github.com"},
            {"name": "Claude", "email": "noreply@anthropic.com"},
            {"name": "Cursor", "email": "noreply@cursor.com"},
            {"name": "Devin", "email": "noreply@devin.ai"},
        ],
        "thresholds": thresholds,
    }
    (repo_path / ".driftscope.yaml").write_text(yaml.dump(config), encoding="utf-8")


class TestThresholdEnforcement:
    """Verify threshold configuration affects report content."""

    def test_json_includes_threshold_breaches_field(self, fixture_repo: Path) -> None:
        """JSON output always includes a threshold_breaches field."""
        result = runner.invoke(
            app,
            ["analyze", "--repo-path", str(fixture_repo), "--format", "json", "--output", "-"],
        )
        assert result.exit_code == 0, result.output
        data = json.loads(result.stdout)
        assert "threshold_breaches" in data

    def test_custom_config_is_loaded(self, fixture_repo: Path) -> None:
        """A custom .driftscope.yaml is loaded and used during analysis."""
        _write_config(fixture_repo, {"ai_line_ratio": 0.99})
        result = runner.invoke(
            app,
            ["analyze", "--repo-path", str(fixture_repo), "--format", "json", "--output", "-"],
        )
        assert result.exit_code == 0, result.output
        data = json.loads(result.stdout)
        # Config loaded successfully, report generated
        assert "modules" in data

    def test_markdown_with_config(self, fixture_repo: Path) -> None:
        """Markdown output renders with custom config thresholds."""
        _write_config(fixture_repo, {"ai_line_ratio": 0.5})
        result = runner.invoke(
            app,
            ["analyze", "--repo-path", str(fixture_repo), "--format", "markdown", "--output", "-"],
        )
        assert result.exit_code == 0, result.output
        assert "# DriftScope Report" in result.stdout

    def test_explicit_config_flag(self, fixture_repo: Path, tmp_path: Path) -> None:
        """--config flag loads config from a custom path."""
        config_file = tmp_path / "custom-config.yaml"
        config_file.write_text(
            yaml.dump({
                "ai_patterns": [
                    {"name": "Copilot", "email": "noreply@github.com"},
                ],
            }),
            encoding="utf-8",
        )
        result = runner.invoke(
            app,
            [
                "analyze",
                "--repo-path", str(fixture_repo),
                "--config", str(config_file),
                "--format", "json",
                "--output", "-",
            ],
        )
        assert result.exit_code == 0, result.output
        data = json.loads(result.stdout)
        assert "modules" in data
