"""GitHub PR comment posting via REST API v3.

Posts a formatted summary comment on a pull request using the
``GITHUB_TOKEN``, ``GITHUB_REPOSITORY``, and ``GITHUB_REF`` environment
variables provided by GitHub Actions.

Network errors are caught and logged — they never cause the workflow to
fail.

Time Complexity: O(1) for API call (single HTTP POST).
"""

from __future__ import annotations

import json
import logging
import os
import re
from pathlib import Path

import requests

from driftscope.errors import DriftScopeError

logger = logging.getLogger(__name__)


class GitHubIntegrationError(DriftScopeError):
    """GitHub integration failures: missing env vars, API errors."""

    def __init__(self, message: str, **kwargs: object) -> None:
        super().__init__(message, stage="integrations", **kwargs)


_GITHUB_API = "https://api.github.com"


def post_pr_comment(summary_path: Path, report_url: str = "") -> None:
    """Post a DriftScope summary comment on the current pull request.

    Args:
        summary_path: Path to the JSON summary file.
        report_url: Optional URL to the full HTML report artifact.

    Raises:
        GitHubIntegrationError: If the summary file does not exist.
    """
    if not summary_path.is_file():
        raise GitHubIntegrationError(
            f"Summary file not found: {summary_path}",
            suggestion="Ensure the analyze step ran before posting comments",
        )

    try:
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("Failed to read summary file: %s", exc)
        return

    try:
        ctx = _extract_pr_context()
    except GitHubIntegrationError as exc:
        logger.warning("Cannot extract PR context: %s", exc.message)
        return

    body = _build_comment_body(summary, report_url=report_url)
    url = f"{_GITHUB_API}/repos/{ctx['owner']}/{ctx['repo']}/issues/{ctx['pr_number']}/comments"
    headers = {
        "Authorization": f"token {ctx['token']}",
        "Accept": "application/vnd.github.v3+json",
    }

    try:
        response = requests.post(url, json={"body": body}, headers=headers, timeout=30)
        if response.status_code not in (200, 201):
            logger.warning(
                "GitHub API returned %d: %s", response.status_code, response.text
            )
        else:
            logger.info("Posted PR comment successfully (id=%s)", response.json().get("id"))
    except Exception as exc:
        logger.warning("Failed to post PR comment: %s", exc)


def _extract_pr_context() -> dict[str, str | int]:
    """Extract owner, repo, PR number, and token from GitHub Actions env vars.

    Returns:
        Dict with keys: owner, repo, pr_number, token.

    Raises:
        GitHubIntegrationError: If required env vars are missing or malformed.
    """
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    if not repo:
        raise GitHubIntegrationError(
            "GITHUB_REPOSITORY environment variable is not set",
            suggestion="This function must run within a GitHub Actions workflow",
        )

    ref = os.environ.get("GITHUB_REF", "")
    if not ref:
        raise GitHubIntegrationError(
            "GITHUB_REF environment variable is not set",
            suggestion="This function must run within a GitHub Actions PR workflow",
        )

    match = re.match(r"^refs/pull/(\d+)/", ref)
    if not match:
        raise GitHubIntegrationError(
            f"GITHUB_REF is not a PR ref: {ref}",
            suggestion="Ensure this step runs in a pull_request workflow event",
        )

    token = os.environ.get("GITHUB_TOKEN", "")
    if not token:
        raise GitHubIntegrationError(
            "GITHUB_TOKEN environment variable is not set",
            suggestion="Ensure the workflow has `permissions: pull-requests: write`",
        )

    owner, repo_name = repo.split("/", 1)
    return {
        "owner": owner,
        "repo": repo_name,
        "pr_number": int(match.group(1)),
        "token": token,
    }


def _build_comment_body(summary: dict, report_url: str = "") -> str:
    """Build a markdown comment body from a JSON summary.

    Args:
        summary: Parsed JSON summary dict.
        report_url: Optional URL to the full HTML report.

    Returns:
        Markdown string for the PR comment.
    """
    lines: list[str] = ["## DriftScope Report\n"]

    modules = summary.get("modules", [])
    if modules:
        lines.append("| Module | AI Lines | Human Lines | Total |")
        lines.append("|--------|----------|-------------|-------|")
        for mod in modules:
            lines.append(
                f"| {mod.get('module_path', '/') or '/'} "
                f"| {mod.get('ai_lines', 0)} "
                f"| {mod.get('human_lines', 0)} "
                f"| {mod.get('total_lines', 0)} |"
            )
        lines.append("")

    breaches = summary.get("threshold_breaches", [])
    if breaches:
        lines.append("### Threshold Breaches\n")
        lines.append("| Metric | Module | Value | Threshold |")
        lines.append("|--------|--------|-------|-----------|")
        for b in breaches:
            lines.append(
                f"| {b.get('metric', '')} "
                f"| {b.get('module_path', '')} "
                f"| {b.get('value', '')} "
                f"| {b.get('threshold', '')} |"
            )
        lines.append("")

    if report_url:
        lines.append(f"[View Full Report]({report_url})\n")

    return "\n".join(lines)
