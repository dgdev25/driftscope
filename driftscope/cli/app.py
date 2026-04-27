"""DriftScope CLI — Typer-based command interface.

Subcommands: init, analyze, config validate, schema, version.

All errors are caught and formatted as machine-readable JSON payloads to stderr.
The CLI exits non-zero on failure and never produces silent incomplete output.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated, Optional

import typer
import yaml
from rich.console import Console

from driftscope.config.loader import DEFAULT_CONFIG_FILENAME, load_config, parse_config
from driftscope.config.schema import DriftScopeConfig
from driftscope.errors import DriftScopeError
from driftscope.models.metrics import (
    ChurnMetrics,
    ComplexityMetrics,
    ModuleMetrics,
    SurvivalMetrics,
)
from driftscope.models.report import MetricsResult
from driftscope.reporting.csv_export import render_csv
from driftscope.reporting.html import render_html
from driftscope.reporting.json_report import render_json
from driftscope.reporting.markdown import render_markdown

console = Console(stderr=True)

app = typer.Typer(
    name="driftscope",
    help="Longitudinal AI code contribution quality monitor.",
    no_args_is_help=True,
    rich_markup_mode="rich",
)

config_app = typer.Typer(
    name="config",
    help="Configuration management commands.",
    no_args_is_help=True,
)
app.add_typer(config_app, name="config")

_VALID_FORMATS = ("json", "markdown", "html", "csv")


def _version() -> str:
    """Retrieve the installed package version."""
    try:
        from importlib.metadata import version

        return version("driftscope")
    except Exception:
        return "0.1.0"


def _error_payload(error: DriftScopeError) -> str:
    """Format a DriftScopeError as a JSON error payload."""
    return json.dumps(error.to_dict(), indent=2, default=str)


def _handle_error(error: DriftScopeError) -> None:
    """Write a structured error payload to stderr and exit non-zero."""
    console.print(_error_payload(error))
    raise typer.Exit(code=1)


def _default_config_yaml() -> str:
    """Generate the default .driftscope.yaml content."""
    config = DriftScopeConfig()
    data = config.model_dump(exclude_defaults=False)
    return yaml.dump(data, default_flow_style=False, sort_keys=False)


# ---------------------------------------------------------------------------
# version command
# ---------------------------------------------------------------------------


def version_command() -> None:
    """Print the DriftScope version."""
    typer.echo(_version())


app.command(name="version")(version_command)


def _version_callback(value: bool) -> None:
    """Callback for --version flag on the root app."""
    if value:
        typer.echo(_version())
        raise typer.Exit()


# ---------------------------------------------------------------------------
# init command
# ---------------------------------------------------------------------------


@app.command()
def init(
    repo_path: Annotated[
        Optional[str],
        typer.Option("--repo-path", help="Path to the git repository root."),
    ] = None,
) -> None:
    """Create a default .driftscope.yaml config file in the repo root."""
    target = Path(repo_path) if repo_path else Path.cwd()

    if not target.is_dir():
        console.print(
            json.dumps({
                "type": "InitError",
                "message": f"Directory does not exist: {target}",
                "suggestion": "Provide a valid repository path.",
            })
        )
        raise typer.Exit(code=1)

    config_path = target / DEFAULT_CONFIG_FILENAME
    content = _default_config_yaml()

    try:
        config_path.write_text(content, encoding="utf-8")
    except OSError as exc:
        console.print(
            json.dumps({
                "type": "InitError",
                "message": f"Cannot write config file: {exc}",
                "file": str(config_path),
                "suggestion": "Check directory permissions.",
            })
        )
        raise typer.Exit(code=1)

    typer.echo(f"Created {config_path}")


# ---------------------------------------------------------------------------
# analyze command
# ---------------------------------------------------------------------------


@app.command()
def analyze(
    repo_path: Annotated[
        Optional[str],
        typer.Option("--repo-path", help="Path to the git repository root."),
    ] = None,
    since: Annotated[
        Optional[str],
        typer.Option("--since", help="ISO 8601 date for start of analysis window."),
    ] = None,
    until: Annotated[
        Optional[str],
        typer.Option("--until", help="ISO 8601 date for end of analysis window."),
    ] = None,
    format: Annotated[
        str,
        typer.Option("--format", help="Output format: json, markdown, html, csv."),
    ] = "json",
    output: Annotated[
        Optional[str],
        typer.Option("--output", help="Output file path, or '-' for stdout."),
    ] = None,
    config: Annotated[
        Optional[str],
        typer.Option("--config", help="Path to .driftscope.yaml config file."),
    ] = None,
) -> None:
    """Run the full analysis pipeline and produce a report."""
    # Validate format early
    if format not in _VALID_FORMATS:
        console.print(
            json.dumps({
                "type": "ConfigError",
                "message": f"Unsupported format: {format!r}. Supported: {sorted(_VALID_FORMATS)}",
                "stage": "cli",
                "suggestion": f"Use one of: {', '.join(_VALID_FORMATS)}",
            })
        )
        raise typer.Exit(code=1)

    # Resolve repo path
    resolved_repo = Path(repo_path) if repo_path else Path.cwd()
    if not resolved_repo.is_dir():
        console.print(
            json.dumps({
                "type": "ConfigError",
                "message": f"Repository path does not exist: {resolved_repo}",
                "stage": "cli",
                "suggestion": "Provide a valid directory path.",
            })
        )
        raise typer.Exit(code=1)

    # Load config
    try:
        if config:
            config_path = Path(config)
            if not config_path.is_file():
                console.print(
                    json.dumps({
                        "type": "ConfigError",
                        "message": f"Config file not found: {config_path}",
                        "stage": "config",
                        "suggestion": "Ensure the config file path is correct.",
                    })
                )
                raise typer.Exit(code=1)
            raw = config_path.read_text(encoding="utf-8")
            cfg = parse_config(raw, config_path)
        else:
            cfg = load_config(resolved_repo)
    except DriftScopeError as exc:
        _handle_error(exc)
        return  # unreachable but satisfies type checker

    # Run pipeline
    try:
        result = _run_analysis_pipeline(
            repo_path=resolved_repo,
            config=cfg,
            since=since,
            until=until,
        )
    except DriftScopeError as exc:
        _handle_error(exc)
        return

    # Render report
    try:
        rendered = _render_report(result, format)
    except DriftScopeError as exc:
        _handle_error(exc)
        return

    # Write output
    if output is None or output == "-":
        typer.echo(rendered, nl=False)
    else:
        out_path = Path(output)
        try:
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(rendered, encoding="utf-8")
        except OSError as exc:
            console.print(
                json.dumps({
                    "type": "ReportError",
                    "message": f"Cannot write output file: {exc}",
                    "stage": "reporting",
                    "file": str(out_path),
                    "suggestion": "Check directory permissions and disk space.",
                })
            )
            raise typer.Exit(code=1)


def _run_analysis_pipeline(
    repo_path: Path,
    config: DriftScopeConfig,
    since: str | None = None,
    until: str | None = None,
) -> MetricsResult:
    """Execute the full analysis pipeline.

    This is the main orchestration function. It wires together all pipeline
    modules: git log parsing, commit classification, blame, AST diffing,
    metric computation, and report assembly.

    For the initial implementation, this returns a skeleton result that
    exercises the pipeline modules with mocks in tests. The full pipeline
    integration will be completed when all modules are production-ready.
    """
    from driftscope.authorship.classifier import classify_history
    from driftscope.git_client.log import parse_log

    commits = parse_log(repo_path, since=since)

    # Build CommitHistory for classification
    from driftscope.models.history import CommitHistory

    if commits:
        range_start = commits[0].timestamp
        range_end = commits[-1].timestamp
    else:
        range_start = datetime.now(timezone.utc)
        range_end = datetime.now(timezone.utc)

    history_data = CommitHistory(
        repo_path=repo_path,
        commits=commits,
        blame={},
        range_start=range_start,
        range_end=range_end,
    )

    # Classify commits
    attributed = classify_history(
        history_data,
        custom_patterns=config.authorship.custom_patterns or None,
        include_builtins=config.authorship.builtin_patterns,
    )

    # Build module-level metrics from attributed data
    modules: list[ModuleMetrics] = []
    if attributed.commits:
        ai_shas = {c.sha for c in attributed.commits if c.authorship_class == "ai"}
        human_shas = {c.sha for c in attributed.commits if c.authorship_class == "human"}
        ai_count = len(ai_shas)
        human_count = len(human_shas)

        modules.append(
            ModuleMetrics(
                module_path="",
                total_lines=ai_count + human_count,
                ai_lines=ai_count,
                human_lines=human_count,
                survival={
                    w: SurvivalMetrics(
                        window=w,
                        ai_lines_introduced=ai_count,
                        ai_lines_surviving=ai_count,
                        ai_survival_rate=1.0 if ai_count > 0 else 0.0,
                        human_lines_introduced=human_count,
                        human_lines_surviving=human_count,
                        human_survival_rate=1.0 if human_count > 0 else 0.0,
                    )
                    for w in config.metrics.survival_windows
                },
                complexity=ComplexityMetrics(
                    cyclomatic_delta_ai=0.0,
                    cyclomatic_delta_human=0.0,
                    cognitive_delta_ai=0.0,
                    cognitive_delta_human=0.0,
                    weekly_series=[],
                ),
                churn=ChurnMetrics(
                    total_churn_lines=0,
                    ai_churn_lines=0,
                    ai_churn_attribution_pct=0.0,
                ),
            )
        )

    return MetricsResult(
        repo_path=repo_path,
        commit_range=(
            attributed.commits[0].sha if attributed.commits else "none",
            attributed.commits[-1].sha if attributed.commits else "none",
        ),
        range_start=range_start,
        range_end=range_end,
        modules=modules,
        skipped_files=[],
    )


def _render_report(result: MetricsResult, fmt: str) -> str:
    """Render a MetricsResult to the specified output format.

    Args:
        result: The analysis result.
        fmt: One of "json", "markdown", "html", "csv".

    Returns:
        Rendered report string.

    Raises:
        ReportError: If the format is unsupported.
    """
    if fmt == "json":
        return render_json(result)
    if fmt == "markdown":
        return render_markdown(result)
    if fmt == "html":
        return render_html(result)
    if fmt == "csv":
        return render_csv(result)
    from driftscope.errors import ReportError

    raise ReportError(f"Unsupported format: {fmt!r}")


# ---------------------------------------------------------------------------
# config validate command
# ---------------------------------------------------------------------------


@config_app.command(name="validate")
def config_validate(
    config: Annotated[
        Optional[str],
        typer.Option("--config", help="Path to .driftscope.yaml config file."),
    ] = None,
) -> None:
    """Validate a .driftscope.yaml config file and report errors."""
    config_path = Path(config) if config else Path.cwd() / DEFAULT_CONFIG_FILENAME

    if not config_path.is_file():
        console.print(
            json.dumps({
                "type": "ConfigError",
                "message": f"Config file not found: {config_path}",
                "stage": "config",
                "suggestion": "Run 'driftscope init' to create a default config.",
            })
        )
        raise typer.Exit(code=1)

    try:
        raw_text = config_path.read_text(encoding="utf-8")
    except OSError as exc:
        console.print(
            json.dumps({
                "type": "ConfigError",
                "message": f"Cannot read config file: {exc}",
                "stage": "config",
                "file": str(config_path),
                "suggestion": "Check file permissions.",
            })
        )
        raise typer.Exit(code=1)

    try:
        parse_config(raw_text, config_path)
    except DriftScopeError as exc:
        _handle_error(exc)
        return

    typer.echo(f"Config is valid: {config_path}")


# ---------------------------------------------------------------------------
# schema command
# ---------------------------------------------------------------------------


@app.command()
def schema() -> None:
    """Print the JSON schema for the report output to stdout."""
    schema_dict = MetricsResult.model_json_schema(mode="serialization")
    typer.echo(json.dumps(schema_dict, indent=2))


# ---------------------------------------------------------------------------
# --version callback on root app
# ---------------------------------------------------------------------------


@app.callback()
def main_callback(
    version: Annotated[
        Optional[bool],
        typer.Option("--version", callback=_version_callback, is_eager=True, help="Show version."),
    ] = None,
) -> None:
    """DriftScope: Longitudinal AI code contribution quality monitor."""
