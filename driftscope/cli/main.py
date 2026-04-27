"""Entry point module for the DriftScope CLI.

This module re-exports the Typer app from ``driftscope.cli.app`` so that
the ``pyproject.toml`` entry point ``driftscope = "driftscope.cli.main:app"``
resolves correctly.
"""

from driftscope.cli.app import app

__all__ = ["app"]
