"""Tests for config file loading."""

from pathlib import Path

import pytest

from driftscope.config.loader import load_config, parse_config
from driftscope.errors import ConfigError


def test_load_config_missing_file_returns_defaults(tmp_path: Path) -> None:
    config = load_config(tmp_path)
    assert config.authorship.builtin_patterns is True
    assert config.output.default_format == "markdown"


def test_load_config_valid_yaml(tmp_path: Path) -> None:
    config_file = tmp_path / ".driftscope.yaml"
    config_file.write_text(
        "authorship:\n"
        "  builtin_patterns: false\n"
        "  custom_patterns:\n"
        "    - 'AI-Generated: .*'\n"
        "output:\n"
        "  default_format: json\n"
    )
    config = load_config(tmp_path)
    assert config.authorship.builtin_patterns is False
    assert config.output.default_format == "json"


def test_load_config_invalid_yaml(tmp_path: Path) -> None:
    config_file = tmp_path / ".driftscope.yaml"
    config_file.write_text("authorship:\n  - broken: [missing")
    with pytest.raises(ConfigError, match="Invalid YAML"):
        load_config(tmp_path)


def test_load_config_invalid_schema(tmp_path: Path) -> None:
    config_file = tmp_path / ".driftscope.yaml"
    config_file.write_text("output:\n  default_format: pdf\n")
    with pytest.raises(ConfigError, match="Config validation failed"):
        load_config(tmp_path)


def test_load_config_non_dict_yaml(tmp_path: Path) -> None:
    config_file = tmp_path / ".driftscope.yaml"
    config_file.write_text("- just\n- a\n- list\n")
    with pytest.raises(ConfigError, match="must be a YAML mapping"):
        load_config(tmp_path)


def test_parse_config_empty_string() -> None:
    config = parse_config("")
    assert config.authorship.builtin_patterns is True


def test_parse_config_null_yaml() -> None:
    config = parse_config("---\n")
    assert config.authorship.builtin_patterns is True


def test_load_config_unreadable_file(tmp_path: Path) -> None:
    config_file = tmp_path / ".driftscope.yaml"
    config_file.write_text("output:\n  default_format: json\n")
    config_file.chmod(0o000)
    try:
        with pytest.raises(ConfigError, match="Cannot read config file"):
            load_config(tmp_path)
    finally:
        config_file.chmod(0o644)
