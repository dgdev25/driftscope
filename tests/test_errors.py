"""Tests for the DriftScope error hierarchy."""

import json

from driftscope.errors import (
    ASTParseError,
    AuthorshipError,
    ConfigError,
    DriftScopeError,
    GitError,
    MetricError,
    ReportError,
)


def test_driftscope_error_is_exception() -> None:
    err = DriftScopeError(message="test")
    assert isinstance(err, Exception)


def test_driftscope_error_to_dict() -> None:
    err = DriftScopeError(
        message="something broke",
        stage="pipeline",
        file="src/main.py",
        suggestion="try again",
    )
    d = err.to_dict()
    assert d["type"] == "DriftScopeError"
    assert d["message"] == "something broke"
    assert d["stage"] == "pipeline"
    assert d["file"] == "src/main.py"
    assert d["suggestion"] == "try again"


def test_driftscope_error_to_dict_serializable() -> None:
    err = DriftScopeError(message="test", stage="s")
    json_str = json.dumps({"error": err.to_dict()})
    assert "DriftScopeError" in json_str


def test_config_error_default_stage() -> None:
    err = ConfigError(message="bad yaml")
    assert err.stage == "config"
    assert isinstance(err, DriftScopeError)


def test_git_error_default_stage() -> None:
    err = GitError(message="not a repo")
    assert err.stage == "git_client"


def test_authorship_error_default_stage() -> None:
    err = AuthorshipError(message="bad regex")
    assert err.stage == "authorship"


def test_ast_parse_error_default_stage() -> None:
    err = ASTParseError(message="parse timeout")
    assert err.stage == "ast_engine"


def test_metric_error_default_stage() -> None:
    err = MetricError(message="division by zero")
    assert err.stage == "metrics"


def test_report_error_default_stage() -> None:
    err = ReportError(message="disk full")
    assert err.stage == "reporting"


def test_error_optional_fields() -> None:
    err = ConfigError(message="bad config")
    assert err.file is None
    assert err.suggestion is None


def test_error_with_all_context() -> None:
    err = ASTParseError(
        message="parse timeout on src/large_file.py (5.2s > 5.0s limit)",
        file="src/large_file.py",
        suggestion="Increase timeout with --parse-timeout or exclude with .driftscope.yaml",
    )
    assert err.file == "src/large_file.py"
    assert "--parse-timeout" in (err.suggestion or "")
