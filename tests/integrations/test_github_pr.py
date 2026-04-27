"""Tests for GitHub PR comment posting integration."""

from __future__ import annotations

import json
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from driftscope.integrations.github_pr import (
    GitHubIntegrationError,
    _build_comment_body,
    _extract_pr_context,
    post_pr_comment,
)


# ---------------------------------------------------------------------------
# _extract_pr_context
# ---------------------------------------------------------------------------


class TestExtractPrContext:
    """Tests for _extract_pr_context."""

    def test_extracts_from_github_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Extracts owner, repo, PR number from GitHub Actions env vars."""
        monkeypatch.setenv("GITHUB_REPOSITORY", "acme/my-app")
        monkeypatch.setenv("GITHUB_REF", "refs/pull/42/merge")
        monkeypatch.setenv("GITHUB_TOKEN", "ghp_test")
        ctx = _extract_pr_context()
        assert ctx["owner"] == "acme"
        assert ctx["repo"] == "my-app"
        assert ctx["pr_number"] == 42

    def test_missing_github_repository_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Raises GitHubIntegrationError when GITHUB_REPOSITORY is unset."""
        monkeypatch.delenv("GITHUB_REPOSITORY", raising=False)
        with pytest.raises(GitHubIntegrationError, match="GITHUB_REPOSITORY"):
            _extract_pr_context()

    def test_missing_github_ref_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Raises GitHubIntegrationError when GITHUB_REF is unset."""
        monkeypatch.setenv("GITHUB_REPOSITORY", "acme/app")
        monkeypatch.delenv("GITHUB_REF", raising=False)
        with pytest.raises(GitHubIntegrationError, match="GITHUB_REF"):
            _extract_pr_context()

    def test_non_pr_ref_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Raises GitHubIntegrationError when GITHUB_REF is not a PR ref."""
        monkeypatch.setenv("GITHUB_REPOSITORY", "acme/app")
        monkeypatch.setenv("GITHUB_REF", "refs/heads/main")
        with pytest.raises(GitHubIntegrationError, match="not a PR"):
            _extract_pr_context()

    def test_missing_token_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Raises GitHubIntegrationError when GITHUB_TOKEN is unset."""
        monkeypatch.setenv("GITHUB_REPOSITORY", "acme/app")
        monkeypatch.setenv("GITHUB_REF", "refs/pull/10/merge")
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        with pytest.raises(GitHubIntegrationError, match="GITHUB_TOKEN"):
            _extract_pr_context()


# ---------------------------------------------------------------------------
# _build_comment_body
# ---------------------------------------------------------------------------


class TestBuildCommentBody:
    """Tests for _build_comment_body."""

    def test_builds_markdown_from_summary(self) -> None:
        """Produces a markdown comment body from a JSON summary."""
        summary = {
            "repo_path": "/repo",
            "commit_range": ["abc", "def"],
            "modules": [
                {
                    "module_path": "src",
                    "total_lines": 100,
                    "ai_lines": 30,
                    "human_lines": 70,
                    "survival": {},
                    "complexity": {
                        "cyclomatic_delta_ai": 5.0,
                        "cyclomatic_delta_human": 10.0,
                    },
                    "churn": {"total_churn_lines": 50},
                },
            ],
            "threshold_breaches": [],
        }
        body = _build_comment_body(summary, report_url="https://example.com/report")
        assert "## DriftScope Report" in body
        assert "src" in body
        assert "| 30 |" in body
        assert "https://example.com/report" in body

    def test_includes_threshold_breaches(self) -> None:
        """Comment body lists threshold breaches when present."""
        summary = {
            "modules": [],
            "threshold_breaches": [
                {"metric": "ai_survival_rate", "module_path": "src", "value": 0.3, "threshold": 0.5},
            ],
        }
        body = _build_comment_body(summary, report_url="")
        assert "Threshold Breaches" in body
        assert "ai_survival_rate" in body

    def test_no_breach_section_when_empty(self) -> None:
        """No breach section when there are no threshold breaches."""
        summary = {"modules": [], "threshold_breaches": []}
        body = _build_comment_body(summary, report_url="")
        assert "Threshold Breaches" not in body


# ---------------------------------------------------------------------------
# post_pr_comment
# ---------------------------------------------------------------------------


class TestPostPrComment:
    """Tests for post_pr_comment with mocked HTTP and env vars."""

    def test_posts_comment_successfully(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """post_pr_comment posts a comment to the correct GitHub API URL."""
        monkeypatch.setenv("GITHUB_REPOSITORY", "acme/app")
        monkeypatch.setenv("GITHUB_REF", "refs/pull/7/merge")
        monkeypatch.setenv("GITHUB_TOKEN", "ghp_test123")

        summary_file = tmp_path / "summary.json"
        summary_file.write_text(
            json.dumps({"modules": [], "threshold_breaches": []}),
            encoding="utf-8",
        )

        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"id": 42}

        with patch("driftscope.integrations.github_pr.requests.post", return_value=mock_response) as mock_post:
            post_pr_comment(summary_file, report_url="https://ci.example.com/report")

        mock_post.assert_called_once()
        call_url = mock_post.call_args[0][0]
        assert "repos/acme/app/issues/7/comments" in call_url

    def test_network_error_does_not_raise(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Network errors are caught and logged, not re-raised."""
        monkeypatch.setenv("GITHUB_REPOSITORY", "acme/app")
        monkeypatch.setenv("GITHUB_REF", "refs/pull/7/merge")
        monkeypatch.setenv("GITHUB_TOKEN", "ghp_test123")

        summary_file = tmp_path / "summary.json"
        summary_file.write_text(
            json.dumps({"modules": [], "threshold_breaches": []}),
            encoding="utf-8",
        )

        with patch(
            "driftscope.integrations.github_pr.requests.post",
            side_effect=Exception("connection refused"),
        ):
            # Should not raise
            post_pr_comment(summary_file, report_url="")

    def test_api_error_response_does_not_raise(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Non-2xx API responses are caught and logged."""
        monkeypatch.setenv("GITHUB_REPOSITORY", "acme/app")
        monkeypatch.setenv("GITHUB_REF", "refs/pull/7/merge")
        monkeypatch.setenv("GITHUB_TOKEN", "ghp_test123")

        summary_file = tmp_path / "summary.json"
        summary_file.write_text(
            json.dumps({"modules": [], "threshold_breaches": []}),
            encoding="utf-8",
        )

        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_response.text = "Forbidden"

        with patch("driftscope.integrations.github_pr.requests.post", return_value=mock_response):
            post_pr_comment(summary_file, report_url="")

    def test_missing_summary_file_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Raises GitHubIntegrationError when the summary file does not exist."""
        monkeypatch.setenv("GITHUB_REPOSITORY", "acme/app")
        monkeypatch.setenv("GITHUB_REF", "refs/pull/7/merge")
        monkeypatch.setenv("GITHUB_TOKEN", "ghp_test123")

        with pytest.raises(GitHubIntegrationError, match="Summary file not found"):
            post_pr_comment(Path("/nonexistent/summary.json"), report_url="")

    def test_invalid_json_summary_does_not_raise(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Invalid JSON in summary file is caught and logged."""
        monkeypatch.setenv("GITHUB_REPOSITORY", "acme/app")
        monkeypatch.setenv("GITHUB_REF", "refs/pull/7/merge")
        monkeypatch.setenv("GITHUB_TOKEN", "ghp_test123")

        summary_file = tmp_path / "summary.json"
        summary_file.write_text("not valid json{{{", encoding="utf-8")

        # Should not raise — just logs a warning
        post_pr_comment(summary_file, report_url="")

    def test_unreadable_summary_does_not_raise(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """OSError reading summary file is caught and logged."""
        monkeypatch.setenv("GITHUB_REPOSITORY", "acme/app")
        monkeypatch.setenv("GITHUB_REF", "refs/pull/7/merge")
        monkeypatch.setenv("GITHUB_TOKEN", "ghp_test123")

        summary_file = tmp_path / "summary.json"
        summary_file.write_text("{}", encoding="utf-8")

        with patch.object(Path, "read_text", side_effect=OSError("permission denied")):
            post_pr_comment(summary_file, report_url="")
