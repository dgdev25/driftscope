"""Shared helpers for metrics computation."""

from __future__ import annotations

from pathlib import Path


def module_of(path: Path) -> str:
    """Return the top-level directory component of *path*.

    Files at the repository root return the empty string.

    Args:
        path: File path relative to repository root.

    Returns:
        Top-level directory name, or "" for root-level files.
    """
    parts = path.parts
    return parts[0] if len(parts) > 1 else ""
