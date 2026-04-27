"""Configuration loading and validation for DriftScope."""

from driftscope.config.schema import DriftScopeConfig
from driftscope.config.loader import load_config

__all__ = ["DriftScopeConfig", "load_config"]
