"""Load .driftscope.yaml configuration files."""

from pathlib import Path

import yaml
from pydantic import ValidationError

from driftscope.config.schema import DriftScopeConfig
from driftscope.errors import ConfigError


DEFAULT_CONFIG_FILENAME = ".driftscope.yaml"


def load_config(repo_path: Path | None = None) -> DriftScopeConfig:
    """Load configuration from a repository path, falling back to defaults.

    Args:
        repo_path: Path to search for .driftscope.yaml. Defaults to cwd.

    Returns:
        Parsed and validated DriftScopeConfig.

    Raises:
        ConfigError: If the config file is unreadable, has invalid YAML,
            or fails schema validation.
    """
    search_path = repo_path or Path.cwd()
    config_path = search_path / DEFAULT_CONFIG_FILENAME

    if not config_path.is_file():
        return DriftScopeConfig()

    try:
        raw_text = config_path.read_text(encoding="utf-8")
    except OSError as e:
        raise ConfigError(
            message=f"Cannot read config file: {config_path}: {e}",
            file=str(config_path),
            suggestion="Check file permissions.",
        ) from e

    return parse_config(raw_text, config_path)


def parse_config(raw_text: str, config_path: Path | None = None) -> DriftScopeConfig:
    """Parse a YAML string into a validated DriftScopeConfig.

    Args:
        raw_text: YAML content to parse.
        config_path: Optional path for error reporting.

    Returns:
        Parsed and validated DriftScopeConfig.

    Raises:
        ConfigError: If the YAML is invalid, is not a mapping,
            or fails schema validation.
    """
    try:
        data = yaml.safe_load(raw_text)
    except yaml.YAMLError as e:
        raise ConfigError(
            message=f"Invalid YAML in config file: {e}",
            file=str(config_path) if config_path else None,
            suggestion="Check YAML syntax at yaml-online-parser.appspot.com.",
        ) from e

    if data is None:
        return DriftScopeConfig()

    if not isinstance(data, dict):
        raise ConfigError(
            message="Config file must be a YAML mapping (key: value pairs).",
            file=str(config_path) if config_path else None,
        )

    try:
        return DriftScopeConfig.model_validate(data)
    except ValidationError as e:
        error_messages = []
        for err in e.errors():
            loc = " -> ".join(str(x) for x in err["loc"])
            error_messages.append(f"  {loc}: {err['msg']}")
        raise ConfigError(
            message="Config validation failed:\n" + "\n".join(error_messages),
            file=str(config_path) if config_path else None,
            suggestion="Run `driftscope config validate` for detailed diagnostics.",
        ) from e
