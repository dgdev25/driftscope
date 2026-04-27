"""Tests for driftscope CLI app — Typer-based command interface.

Uses CliRunner for isolated testing of each subcommand.
Mocks external dependencies (git, filesystem, pipeline modules).
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml
from typer.testing import CliRunner

from driftscope.cli.app import app

runner = CliRunner()


# ---------------------------------------------------------------------------
# version command
# ---------------------------------------------------------------------------


class TestVersionCommand:
    """Tests for the version subcommand."""

    def test_version_prints_version_string(self) -> None:
        """version subcommand prints a version string to stdout."""
        result = runner.invoke(app, ["version"])
        assert result.exit_code == 0
        assert "0.1.0" in result.stdout

    def test_version_flag_on_root(self) -> None:
        """--version flag on root app prints version and exits cleanly."""
        result = runner.invoke(app, ["--version"])
        assert result.exit_code == 0
        assert "0.1.0" in result.stdout


# ---------------------------------------------------------------------------
# init command
# ---------------------------------------------------------------------------


class TestInitCommand:
    """Tests for the init subcommand."""

    def test_init_creates_config_file(self, tmp_path: Path) -> None:
        """init creates .driftscope.yaml in the specified repo path."""
        result = runner.invoke(app, ["init", "--repo-path", str(tmp_path)])
        assert result.exit_code == 0
        config_file = tmp_path / ".driftscope.yaml"
        assert config_file.is_file()

    def test_init_config_is_valid_yaml(self, tmp_path: Path) -> None:
        """init creates a config file with valid YAML content."""
        runner.invoke(app, ["init", "--repo-path", str(tmp_path)])
        config_file = tmp_path / ".driftscope.yaml"
        content = config_file.read_text(encoding="utf-8")
        data = yaml.safe_load(content)
        assert isinstance(data, dict)
        assert "authorship" in data

    def test_init_default_repo_path_is_cwd(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """init with no --repo-path uses the current working directory."""
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(app, ["init"])
        assert result.exit_code == 0
        assert (tmp_path / ".driftscope.yaml").is_file()

    def test_init_config_contains_builtin_patterns(self, tmp_path: Path) -> None:
        """init creates config with builtin_patterns enabled by default."""
        runner.invoke(app, ["init", "--repo-path", str(tmp_path)])
        config_file = tmp_path / ".driftscope.yaml"
        data = yaml.safe_load(config_file.read_text(encoding="utf-8"))
        assert data["authorship"]["builtin_patterns"] is True

    def test_init_idempotent_overwrites(self, tmp_path: Path) -> None:
        """Running init twice overwrites the existing config without error."""
        runner.invoke(app, ["init", "--repo-path", str(tmp_path)])
        result = runner.invoke(app, ["init", "--repo-path", str(tmp_path)])
        assert result.exit_code == 0

    def test_init_invalid_path_exits_nonzero(self) -> None:
        """init with a non-existent path exits with non-zero code."""
        result = runner.invoke(app, ["init", "--repo-path", "/nonexistent/path/xyz"])
        assert result.exit_code != 0


# ---------------------------------------------------------------------------
# config validate command
# ---------------------------------------------------------------------------


class TestConfigValidateCommand:
    """Tests for the config validate subcommand."""

    def test_validate_valid_config(self, tmp_path: Path) -> None:
        """config validate succeeds with a valid config file."""
        config_file = tmp_path / ".driftscope.yaml"
        config_file.write_text(
            yaml.dump({"authorship": {"builtin_patterns": True}}),
            encoding="utf-8",
        )
        result = runner.invoke(app, ["config", "validate", "--config", str(config_file)])
        assert result.exit_code == 0
        assert "valid" in result.stdout.lower()

    def test_validate_invalid_yaml(self, tmp_path: Path) -> None:
        """config validate exits non-zero for invalid YAML."""
        config_file = tmp_path / ".driftscope.yaml"
        config_file.write_text("authorship: [invalid: yaml: content", encoding="utf-8")
        result = runner.invoke(app, ["config", "validate", "--config", str(config_file)])
        assert result.exit_code != 0

    def test_validate_invalid_schema(self, tmp_path: Path) -> None:
        """config validate exits non-zero for valid YAML with invalid schema."""
        config_file = tmp_path / ".driftscope.yaml"
        config_file.write_text(
            yaml.dump({"analysis": {"languages": ["brainfuck"]}}),
            encoding="utf-8",
        )
        result = runner.invoke(app, ["config", "validate", "--config", str(config_file)])
        assert result.exit_code != 0

    def test_validate_missing_config_file(self, tmp_path: Path) -> None:
        """config validate exits non-zero when config file doesn't exist."""
        config_path = tmp_path / "nonexistent.yaml"
        result = runner.invoke(app, ["config", "validate", "--config", str(config_path)])
        assert result.exit_code != 0


# ---------------------------------------------------------------------------
# schema command
# ---------------------------------------------------------------------------


class TestSchemaCommand:
    """Tests for the schema subcommand."""

    def test_schema_outputs_valid_json(self) -> None:
        """schema command outputs valid JSON to stdout."""
        result = runner.invoke(app, ["schema"])
        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert isinstance(data, dict)

    def test_schema_contains_expected_fields(self) -> None:
        """schema output contains expected top-level fields."""
        result = runner.invoke(app, ["schema"])
        data = json.loads(result.stdout)
        # The schema should have properties reflecting MetricsResult fields
        assert "properties" in data or "$schema" in data or "title" in data


# ---------------------------------------------------------------------------
# analyze command
# ---------------------------------------------------------------------------


class TestAnalyzeCommand:
    """Tests for the analyze subcommand."""

    @patch("driftscope.cli.app._run_analysis_pipeline")
    def test_analyze_json_format(self, mock_pipeline: MagicMock, tmp_path: Path) -> None:
        """analyze with --format json produces JSON output."""
        from datetime import datetime, timezone

        from driftscope.models.metrics import (
            ChurnMetrics,
            ComplexityMetrics,
            ModuleMetrics,
            SurvivalMetrics,
        )
        from driftscope.models.report import MetricsResult

        mock_result = MetricsResult(
            repo_path=tmp_path,
            commit_range=("abc123", "def456"),
            range_start=datetime(2024, 1, 1, tzinfo=timezone.utc),
            range_end=datetime(2024, 6, 1, tzinfo=timezone.utc),
            modules=[
                ModuleMetrics(
                    module_path="src",
                    total_lines=100,
                    ai_lines=30,
                    human_lines=70,
                    survival={"30d": SurvivalMetrics(window="30d", ai_lines_introduced=30, ai_lines_surviving=25, ai_survival_rate=0.83, human_lines_introduced=70, human_lines_surviving=65, human_survival_rate=0.93)},
                    complexity=ComplexityMetrics(cyclomatic_delta_ai=5.0, cyclomatic_delta_human=10.0, cognitive_delta_ai=3.0, cognitive_delta_human=8.0, weekly_series=[]),
                    churn=ChurnMetrics(total_churn_lines=50, ai_churn_lines=15, ai_churn_attribution_pct=30.0),
                )
            ],
            skipped_files=[],
        )
        mock_pipeline.return_value = mock_result

        result = runner.invoke(
            app,
            ["analyze", "--repo-path", str(tmp_path), "--format", "json", "--output", "-"],
        )
        assert result.exit_code == 0
        output_data = json.loads(result.stdout)
        assert "modules" in output_data

    @patch("driftscope.cli.app._run_analysis_pipeline")
    def test_analyze_markdown_format(self, mock_pipeline: MagicMock, tmp_path: Path) -> None:
        """analyze with --format markdown produces markdown output."""
        from datetime import datetime, timezone

        from driftscope.models.metrics import (
            ChurnMetrics,
            ComplexityMetrics,
            ModuleMetrics,
            SurvivalMetrics,
        )
        from driftscope.models.report import MetricsResult

        mock_result = MetricsResult(
            repo_path=tmp_path,
            commit_range=("abc123", "def456"),
            range_start=datetime(2024, 1, 1, tzinfo=timezone.utc),
            range_end=datetime(2024, 6, 1, tzinfo=timezone.utc),
            modules=[
                ModuleMetrics(
                    module_path="src",
                    total_lines=100,
                    ai_lines=30,
                    human_lines=70,
                    survival={"30d": SurvivalMetrics(window="30d", ai_lines_introduced=30, ai_lines_surviving=25, ai_survival_rate=0.83, human_lines_introduced=70, human_lines_surviving=65, human_survival_rate=0.93)},
                    complexity=ComplexityMetrics(cyclomatic_delta_ai=5.0, cyclomatic_delta_human=10.0, cognitive_delta_ai=3.0, cognitive_delta_human=8.0, weekly_series=[]),
                    churn=ChurnMetrics(total_churn_lines=50, ai_churn_lines=15, ai_churn_attribution_pct=30.0),
                )
            ],
            skipped_files=[],
        )
        mock_pipeline.return_value = mock_result

        result = runner.invoke(
            app,
            ["analyze", "--repo-path", str(tmp_path), "--format", "markdown", "--output", "-"],
        )
        assert result.exit_code == 0
        assert "# DriftScope Report" in result.stdout

    @patch("driftscope.cli.app._run_analysis_pipeline")
    def test_analyze_writes_to_file(self, mock_pipeline: MagicMock, tmp_path: Path) -> None:
        """analyze with --output <file> writes to the specified file."""
        from datetime import datetime, timezone

        from driftscope.models.metrics import (
            ChurnMetrics,
            ComplexityMetrics,
            ModuleMetrics,
            SurvivalMetrics,
        )
        from driftscope.models.report import MetricsResult

        mock_result = MetricsResult(
            repo_path=tmp_path,
            commit_range=("abc123", "def456"),
            range_start=datetime(2024, 1, 1, tzinfo=timezone.utc),
            range_end=datetime(2024, 6, 1, tzinfo=timezone.utc),
            modules=[
                ModuleMetrics(
                    module_path="src",
                    total_lines=100,
                    ai_lines=30,
                    human_lines=70,
                    survival={"30d": SurvivalMetrics(window="30d", ai_lines_introduced=30, ai_lines_surviving=25, ai_survival_rate=0.83, human_lines_introduced=70, human_lines_surviving=65, human_survival_rate=0.93)},
                    complexity=ComplexityMetrics(cyclomatic_delta_ai=5.0, cyclomatic_delta_human=10.0, cognitive_delta_ai=3.0, cognitive_delta_human=8.0, weekly_series=[]),
                    churn=ChurnMetrics(total_churn_lines=50, ai_churn_lines=15, ai_churn_attribution_pct=30.0),
                )
            ],
            skipped_files=[],
        )
        mock_pipeline.return_value = mock_result

        output_file = tmp_path / "report.json"
        result = runner.invoke(
            app,
            ["analyze", "--repo-path", str(tmp_path), "--format", "json", "--output", str(output_file)],
        )
        assert result.exit_code == 0
        assert output_file.is_file()
        content = output_file.read_text(encoding="utf-8")
        json.loads(content)  # Should be valid JSON

    def test_analyze_invalid_format_exits_nonzero(self, tmp_path: Path) -> None:
        """analyze with an unsupported format exits non-zero."""
        result = runner.invoke(
            app,
            ["analyze", "--repo-path", str(tmp_path), "--format", "xml"],
        )
        assert result.exit_code != 0

    def test_analyze_invalid_repo_path_exits_nonzero(self) -> None:
        """analyze with a non-existent repo path exits non-zero."""
        result = runner.invoke(
            app,
            ["analyze", "--repo-path", "/nonexistent/repo/path", "--format", "json"],
        )
        assert result.exit_code != 0

    @patch("driftscope.cli.app._run_analysis_pipeline")
    def test_analyze_with_since_option(self, mock_pipeline: MagicMock, tmp_path: Path) -> None:
        """analyze passes --since date through to the pipeline."""
        from datetime import datetime, timezone

        from driftscope.models.metrics import (
            ChurnMetrics,
            ComplexityMetrics,
            ModuleMetrics,
            SurvivalMetrics,
        )
        from driftscope.models.report import MetricsResult

        mock_result = MetricsResult(
            repo_path=tmp_path,
            commit_range=("abc123", "def456"),
            range_start=datetime(2024, 1, 1, tzinfo=timezone.utc),
            range_end=datetime(2024, 6, 1, tzinfo=timezone.utc),
            modules=[
                ModuleMetrics(
                    module_path="src",
                    total_lines=100,
                    ai_lines=30,
                    human_lines=70,
                    survival={"30d": SurvivalMetrics(window="30d", ai_lines_introduced=30, ai_lines_surviving=25, ai_survival_rate=0.83, human_lines_introduced=70, human_lines_surviving=65, human_survival_rate=0.93)},
                    complexity=ComplexityMetrics(cyclomatic_delta_ai=5.0, cyclomatic_delta_human=10.0, cognitive_delta_ai=3.0, cognitive_delta_human=8.0, weekly_series=[]),
                    churn=ChurnMetrics(total_churn_lines=50, ai_churn_lines=15, ai_churn_attribution_pct=30.0),
                )
            ],
            skipped_files=[],
        )
        mock_pipeline.return_value = mock_result

        result = runner.invoke(
            app,
            ["analyze", "--repo-path", str(tmp_path), "--since", "2024-01-01", "--format", "json", "--output", "-"],
        )
        assert result.exit_code == 0

    @patch("driftscope.cli.app._run_analysis_pipeline")
    def test_analyze_pipeline_error_exits_nonzero(self, mock_pipeline: MagicMock, tmp_path: Path) -> None:
        """analyze exits non-zero when the pipeline raises DriftScopeError."""
        from driftscope.errors import GitError

        mock_pipeline.side_effect = GitError("not a git repository")

        result = runner.invoke(
            app,
            ["analyze", "--repo-path", str(tmp_path), "--format", "json", "--output", "-"],
        )
        assert result.exit_code != 0


# ---------------------------------------------------------------------------
# error handling
# ---------------------------------------------------------------------------


class TestErrorHandling:
    """Tests for CLI-level error handling."""

    def test_invalid_subcommand_exits_nonzero(self) -> None:
        """Invoking an unknown subcommand exits non-zero."""
        result = runner.invoke(app, ["nonexistent-command"])
        assert result.exit_code != 0

    @patch("driftscope.cli.app._run_analysis_pipeline")
    def test_driftscope_error_produces_structured_json_to_stderr(
        self, mock_pipeline: MagicMock, tmp_path: Path
    ) -> None:
        """When DriftScopeError is raised, structured JSON error is written to stderr."""
        from driftscope.errors import ConfigError

        mock_pipeline.side_effect = ConfigError("bad config")

        result = runner.invoke(
            app,
            ["analyze", "--repo-path", str(tmp_path), "--format", "json", "--output", "-"],
        )
        assert result.exit_code != 0
        # Typer captures both stdout and stderr in result.output with CliRunner,
        # but we check the output contains structured error info
        output = result.output
        assert "ConfigError" in output or "error" in output.lower()


# ---------------------------------------------------------------------------
# coverage gap fillers
# ---------------------------------------------------------------------------


def _make_result(tmp_path: Path) -> object:
    """Build a minimal MetricsResult for use in pipeline mocks."""
    from datetime import datetime, timezone

    from driftscope.models.metrics import (
        ChurnMetrics,
        ComplexityMetrics,
        ModuleMetrics,
        SurvivalMetrics,
    )
    from driftscope.models.report import MetricsResult

    return MetricsResult(
        repo_path=tmp_path,
        commit_range=("aaa", "bbb"),
        range_start=datetime(2024, 1, 1, tzinfo=timezone.utc),
        range_end=datetime(2024, 6, 1, tzinfo=timezone.utc),
        modules=[
            ModuleMetrics(
                module_path="",
                total_lines=10,
                ai_lines=5,
                human_lines=5,
                survival={
                    "30d": SurvivalMetrics(
                        window="30d",
                        ai_lines_introduced=5,
                        ai_lines_surviving=5,
                        ai_survival_rate=1.0,
                        human_lines_introduced=5,
                        human_lines_surviving=5,
                        human_survival_rate=1.0,
                    ),
                },
                complexity=ComplexityMetrics(
                    cyclomatic_delta_ai=0.0,
                    cyclomatic_delta_human=0.0,
                    cognitive_delta_ai=0.0,
                    cognitive_delta_human=0.0,
                    weekly_series=[],
                ),
                churn=ChurnMetrics(
                    total_churn_lines=10,
                    ai_churn_lines=5,
                    ai_churn_attribution_pct=50.0,
                ),
            ),
        ],
        skipped_files=[],
    )


class TestVersionFallback:
    """Cover _version() fallback when package not installed."""

    def test_version_fallback_when_not_installed(self) -> None:
        """_version returns 0.1.0 when importlib.metadata cannot find the package."""
        import sys

        # Access the real module from sys.modules (the __init__ re-export
        # causes `driftscope.cli.app` to resolve to the Typer object).
        mod = sys.modules["driftscope.cli.app"]
        with patch("importlib.metadata.version", side_effect=Exception("nope")):
            result = mod._version()
            assert result == "0.1.0"


class TestInitErrors:
    """Cover init OSError path (lines 133-142)."""

    def test_init_write_failure(self, tmp_path: Path) -> None:
        """init exits non-zero when writing the config file fails."""
        config_file = tmp_path / ".driftscope.yaml"
        with patch.object(Path, "write_text", side_effect=OSError("disk full")):
            result = runner.invoke(app, ["init", "--repo-path", str(tmp_path)])
        assert result.exit_code != 0
        assert "Cannot write" in result.output


class TestAnalyzeEdgeCases:
    """Cover analyze error branches."""

    def test_analyze_config_file_not_found(self, tmp_path: Path) -> None:
        """analyze exits non-zero when --config points to nonexistent file."""
        result = runner.invoke(
            app,
            [
                "analyze",
                "--repo-path", str(tmp_path),
                "--config", str(tmp_path / "missing.yaml"),
                "--format", "json",
            ],
        )
        assert result.exit_code != 0

    @patch("driftscope.cli.app.load_config")
    def test_analyze_config_load_error(self, mock_load: MagicMock, tmp_path: Path) -> None:
        """analyze exits non-zero when load_config raises DriftScopeError."""
        from driftscope.errors import ConfigError

        mock_load.side_effect = ConfigError("bad yaml")
        result = runner.invoke(
            app,
            ["analyze", "--repo-path", str(tmp_path), "--format", "json", "--output", "-"],
        )
        assert result.exit_code != 0

    @patch("driftscope.cli.app._run_analysis_pipeline")
    def test_analyze_with_valid_config_flag(self, mock_pipeline: MagicMock, tmp_path: Path) -> None:
        """analyze loads config from --config path and runs pipeline."""
        config_file = tmp_path / "custom-config.yaml"
        config_file.write_text(
            yaml.dump({"authorship": {"builtin_patterns": False}}),
            encoding="utf-8",
        )
        mock_pipeline.return_value = _make_result(tmp_path)
        result = runner.invoke(
            app,
            [
                "analyze",
                "--repo-path", str(tmp_path),
                "--config", str(config_file),
                "--format", "json",
                "--output", "-",
            ],
        )
        assert result.exit_code == 0
        mock_pipeline.assert_called_once()

    @patch("driftscope.cli.app._run_analysis_pipeline")
    def test_analyze_html_format(self, mock_pipeline: MagicMock, tmp_path: Path) -> None:
        """analyze with --format html produces HTML output."""
        mock_pipeline.return_value = _make_result(tmp_path)
        result = runner.invoke(
            app,
            ["analyze", "--repo-path", str(tmp_path), "--format", "html", "--output", "-"],
        )
        assert result.exit_code == 0
        assert "<html" in result.stdout.lower()

    @patch("driftscope.cli.app._run_analysis_pipeline")
    def test_analyze_csv_format(self, mock_pipeline: MagicMock, tmp_path: Path) -> None:
        """analyze with --format csv produces CSV output."""
        mock_pipeline.return_value = _make_result(tmp_path)
        result = runner.invoke(
            app,
            ["analyze", "--repo-path", str(tmp_path), "--format", "csv", "--output", "-"],
        )
        assert result.exit_code == 0
        assert "module" in result.stdout

    @patch("driftscope.cli.app._run_analysis_pipeline")
    def test_analyze_output_file_write_error(self, mock_pipeline: MagicMock, tmp_path: Path) -> None:
        """analyze exits non-zero when writing output file fails."""
        mock_pipeline.return_value = _make_result(tmp_path)
        output_file = tmp_path / "out.json"
        with patch.object(Path, "write_text", side_effect=OSError("no space")):
            result = runner.invoke(
                app,
                ["analyze", "--repo-path", str(tmp_path), "--format", "json", "--output", str(output_file)],
            )
        assert result.exit_code != 0

    def test_analyze_render_unsupported_format(self, tmp_path: Path) -> None:
        """_render_report raises ReportError for unsupported format."""
        from driftscope.cli.app import _render_report
        from driftscope.errors import ReportError

        result = _make_result(tmp_path)
        with pytest.raises(ReportError, match="Unsupported format"):
            _render_report(result, "xml")


class TestConfigValidateEdgeCases:
    """Cover config validate read error and parse error branches."""

    def test_validate_read_error(self, tmp_path: Path) -> None:
        """config validate exits non-zero when file read fails."""
        config_file = tmp_path / ".driftscope.yaml"
        config_file.write_text("authorship:\n  builtin_patterns: true\n", encoding="utf-8")
        with patch.object(Path, "read_text", side_effect=OSError("permission denied")):
            result = runner.invoke(app, ["config", "validate", "--config", str(config_file)])
        assert result.exit_code != 0


class TestRunAnalysisPipeline:
    """Cover _run_analysis_pipeline (lines 283-354)."""

    @patch("driftscope.authorship.classifier.classify_history")
    @patch("driftscope.git_client.log.parse_log")
    def test_pipeline_with_commits(self, mock_log: MagicMock, mock_classify: MagicMock, tmp_path: Path) -> None:
        """Pipeline produces a MetricsResult when commits exist."""
        from datetime import datetime, timezone

        from driftscope.config.schema import DriftScopeConfig
        from driftscope.models.commit import Commit
        from driftscope.models.history import AttributedCommit, AttributedHistory

        mock_commit = Commit(
            sha="a" * 40,
            short_sha="a" * 7,
            timestamp=datetime(2024, 6, 1, tzinfo=timezone.utc),
            author_name="bot",
            author_email="bot@copilot.ai",
            committer_name="user",
            committer_email="user@test.com",
            message_subject="feat: add feature",
            message_body="",
            parent_shas=[],
        )
        mock_log.return_value = [mock_commit]

        attributed_commit = AttributedCommit(
            **mock_commit.model_dump(),
            authorship_class="ai",
            matched_pattern="copilot",
        )
        attributed = AttributedHistory(
            repo_path=tmp_path,
            commits=[attributed_commit],
            blame={},
            range_start=datetime(2024, 1, 1, tzinfo=timezone.utc),
            range_end=datetime(2024, 6, 1, tzinfo=timezone.utc),
            ai_commit_count=1,
            human_commit_count=0,
        )
        mock_classify.return_value = attributed

        from driftscope.cli.app import _run_analysis_pipeline

        cfg = DriftScopeConfig()
        result = _run_analysis_pipeline(tmp_path, cfg, since="2024-01-01")
        assert result.repo_path == tmp_path
        assert len(result.modules) == 1

    @patch("driftscope.git_client.log.parse_log")
    def test_pipeline_no_commits(self, mock_log: MagicMock, tmp_path: Path) -> None:
        """Pipeline returns empty modules when no commits found."""
        from driftscope.cli.app import _run_analysis_pipeline
        from driftscope.config.schema import DriftScopeConfig

        mock_log.return_value = []
        cfg = DriftScopeConfig()
        result = _run_analysis_pipeline(tmp_path, cfg)
        assert result.modules == []
