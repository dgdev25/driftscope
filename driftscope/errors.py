"""DriftScope error hierarchy.

Every error inherits from DriftScopeError. Each subclass maps to a pipeline
stage and carries structured context for JSON error output to stderr.
"""


class DriftScopeError(Exception):
    """Base error for all DriftScope failures.

    Attributes:
        message: Human-readable error description.
        stage: Pipeline stage where the error occurred (e.g., "git_client").
        file: Optional file path related to the error.
        suggestion: Optional remediation hint.
    """

    def __init__(
        self,
        message: str,
        stage: str = "",
        file: str | None = None,
        suggestion: str | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.stage = stage
        self.file = file
        self.suggestion = suggestion

    def to_dict(self) -> dict[str, str | None]:
        """Serialize to the structured JSON error format for stderr."""
        return {
            "type": type(self).__name__,
            "message": self.message,
            "stage": self.stage,
            "file": self.file,
            "suggestion": self.suggestion,
        }


class ConfigError(DriftScopeError):
    """Invalid .driftscope.yaml: bad regex, missing required field, unknown key."""

    def __init__(self, message: str, **kwargs: object) -> None:
        super().__init__(message, stage="config", **kwargs)


class GitError(DriftScopeError):
    """git binary failures: not a repo, no history, authentication issue, binary not found."""

    def __init__(self, message: str, **kwargs: object) -> None:
        super().__init__(message, stage="git_client", **kwargs)


class AuthorshipError(DriftScopeError):
    """Pattern compilation failures: invalid regex in custom patterns."""

    def __init__(self, message: str, **kwargs: object) -> None:
        super().__init__(message, stage="authorship", **kwargs)


class ASTParseError(DriftScopeError):
    """tree-sitter parsing failures: unsupported language, corrupted grammar, file too large."""

    def __init__(self, message: str, **kwargs: object) -> None:
        super().__init__(message, stage="ast_engine", **kwargs)


class MetricError(DriftScopeError):
    """Computation failures: empty window, insufficient data, division by zero."""

    def __init__(self, message: str, **kwargs: object) -> None:
        super().__init__(message, stage="metrics", **kwargs)


class ReportError(DriftScopeError):
    """Output failures: disk full, permission denied, template rendering error."""

    def __init__(self, message: str, **kwargs: object) -> None:
        super().__init__(message, stage="reporting", **kwargs)
