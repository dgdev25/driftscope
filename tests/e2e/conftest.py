"""E2E test fixtures — synthetic git repo creation."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import git
import pytest

# gitpython expects git-internal timestamp format: "YYYY-MM-DD HH:MM:SS +0000"
_COMMIT_DATES = {
    1: "2024-01-15 10:00:00 +0000",
    2: "2024-02-01 10:00:00 +0000",
    3: "2024-03-01 10:00:00 +0000",
    4: "2024-03-15 10:00:00 +0000",
    5: "2024-04-01 10:00:00 +0000",
    6: "2024-05-01 10:00:00 +0000",
    7: "2024-05-15 10:00:00 +0000",
    8: "2024-06-01 10:00:00 +0000",
}


@pytest.fixture()
def fixture_repo(tmp_path: Path) -> Path:
    """Create a synthetic git repository with known commit history.

    The repo contains:
    - Two modules: ``src/payments/`` and ``src/auth/``
    - Python files with simple functions
    - A mix of human commits and AI-co-authored commits
    - Known patterns for complexity and churn

    Returns:
        Path to the repository root.
    """
    repo_path = tmp_path / "fixture-repo"
    repo_path.mkdir()
    repo = git.Repo.init(repo_path)

    # Configure author for reproducibility
    repo.config_writer().set_value("user", "name", "Test Author").release()
    repo.config_writer().set_value("user", "email", "test@example.com").release()

    # Create module directories
    payments_dir = repo_path / "src" / "payments"
    payments_dir.mkdir(parents=True)
    auth_dir = repo_path / "src" / "auth"
    auth_dir.mkdir(parents=True)

    # --- Commit 1: Initial structure (human) ---
    (payments_dir / "__init__.py").write_text("", encoding="utf-8")
    (auth_dir / "__init__.py").write_text("", encoding="utf-8")
    (repo_path / "README.md").write_text("# Test Repo\n", encoding="utf-8")
    repo.index.add(["src/payments/__init__.py", "src/auth/__init__.py", "README.md"])
    repo.index.commit("Initial project structure", commit_date=_COMMIT_DATES[1])

    # --- Commit 2: Add payment processing (human) ---
    (payments_dir / "process.py").write_text(
        "def process_payment(amount):\n    return amount > 0\n",
        encoding="utf-8",
    )
    repo.index.add(["src/payments/process.py"])
    repo.index.commit("Add payment processing", commit_date=_COMMIT_DATES[2])

    # --- Commit 3: AI-assisted auth module (Copilot co-author) ---
    (auth_dir / "login.py").write_text(
        "def login(username, password):\n    if username and password:\n        return True\n    return False\n",
        encoding="utf-8",
    )
    repo.index.add(["src/auth/login.py"])
    repo.index.commit(
        "Add login function\n\nCo-authored-by: GitHub Copilot <noreply@github.com>",
        commit_date=_COMMIT_DATES[3],
    )

    # --- Commit 4: Refactor payment (human) ---
    (payments_dir / "process.py").write_text(
        "def process_payment(amount, currency='USD'):\n    if amount <= 0:\n        raise ValueError('Invalid amount')\n    return {'amount': amount, 'currency': currency}\n",
        encoding="utf-8",
    )
    repo.index.add(["src/payments/process.py"])
    repo.index.commit("Refactor payment processing with validation", commit_date=_COMMIT_DATES[4])

    # --- Commit 5: AI-generated auth middleware (Claude Code) ---
    (auth_dir / "middleware.py").write_text(
        "def check_auth(token):\n    if not token:\n        return False\n    if token.startswith('Bearer '):\n        return True\n    return False\n",
        encoding="utf-8",
    )
    repo.index.add(["src/auth/middleware.py"])
    repo.index.commit(
        "Add auth middleware\n\nCo-authored-by: Claude <noreply@anthropic.com>",
        commit_date=_COMMIT_DATES[5],
    )

    # --- Commit 6: Add more payment logic (Cursor) ---
    (payments_dir / "refund.py").write_text(
        "def refund(payment_id, amount):\n    if amount < 0:\n        raise ValueError('Negative refund')\n    return {'refund': amount}\n",
        encoding="utf-8",
    )
    repo.index.add(["src/payments/refund.py"])
    repo.index.commit(
        "Add refund processing\n\nCo-authored-by: Cursor <noreply@cursor.com>",
        commit_date=_COMMIT_DATES[6],
    )

    # --- Commit 7: Bug fix (human) ---
    (payments_dir / "process.py").write_text(
        "def process_payment(amount, currency='USD'):\n    if amount is None or amount <= 0:\n        raise ValueError('Invalid amount')\n    return {'amount': amount, 'currency': currency}\n",
        encoding="utf-8",
    )
    repo.index.add(["src/payments/process.py"])
    repo.index.commit("Fix None handling in payment processing", commit_date=_COMMIT_DATES[7])

    # --- Commit 8: AI security patch (Devin) ---
    (auth_dir / "middleware.py").write_text(
        "import hmac\n\ndef check_auth(token):\n    if not token:\n        return False\n    if token.startswith('Bearer '):\n        return len(token) > 10\n    return False\n",
        encoding="utf-8",
    )
    repo.index.add(["src/auth/middleware.py"])
    repo.index.commit(
        "Add token length validation\n\nCo-authored-by: Devin <noreply@devin.ai>",
        commit_date=_COMMIT_DATES[8],
    )

    return repo_path
