"""SQLite-backed cache for incremental AST analysis.

Stores parsed AST results keyed by (repo_path, commit_sha, file_path) so
re-running analysis on the same commit is idempotent and fast.

Time Complexity:
    get / is_cached:   O(1) indexed lookup
    put:               O(1) upsert via ON CONFLICT
    invalidate:        O(n) where n = rows matching grammar_version

All DB errors are wrapped in CacheError.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from driftscope.errors import DriftScopeError

_SCHEMA = """\
CREATE TABLE IF NOT EXISTS cache_entries (
    repo_path       TEXT    NOT NULL,
    commit_sha      TEXT    NOT NULL,
    file_path       TEXT    NOT NULL,
    ast_hash        TEXT    NOT NULL,
    ast_data        TEXT    NOT NULL,
    grammar_version TEXT    NOT NULL,
    timestamp       TEXT    NOT NULL,
    PRIMARY KEY (repo_path, commit_sha, file_path)
);
"""


class CacheError(DriftScopeError):
    """Database failures during cache operations."""

    def __init__(self, message: str, **kwargs: object) -> None:
        super().__init__(message, stage="cache", **kwargs)


class CacheManager:
    """Manage a SQLite-backed cache for AST analysis results.

    Args:
        db_path: Filesystem path for the SQLite database. Parent directories
                 are created automatically.

    Raises:
        CacheError: If the database or its parent directory cannot be created.
    """

    def __init__(self, db_path: Path) -> None:
        try:
            db_path.parent.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise CacheError(
                f"Cannot create cache directory {db_path.parent}: {exc}"
            ) from exc

        try:
            self._conn = sqlite3.connect(str(db_path))
        except sqlite3.Error as exc:
            raise CacheError(
                f"Cannot open cache database at {db_path}: {exc}"
            ) from exc

        self._conn.execute("PRAGMA journal_mode=WAL;")
        self._conn.execute("PRAGMA synchronous=NORMAL;")
        self._conn.executescript(_SCHEMA)
        self._conn.commit()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get(self, repo_path: str, commit_sha: str, file_path: str) -> str | None:
        """Retrieve cached AST data.

        Args:
            repo_path: Absolute path to the repository root.
            commit_sha: Full 40-character commit SHA.
            file_path: Repository-relative file path.

        Returns:
            The cached ``ast_data`` string, or ``None`` if no entry exists.

        Raises:
            CacheError: On database query failure.
        """
        try:
            cursor = self._conn.execute(
                "SELECT ast_data FROM cache_entries "
                "WHERE repo_path = ? AND commit_sha = ? AND file_path = ?",
                (repo_path, commit_sha, file_path),
            )
            row = cursor.fetchone()
            return row[0] if row is not None else None
        except sqlite3.Error as exc:
            raise CacheError(f"Cache get failed: {exc}") from exc

    def put(
        self,
        repo_path: str,
        commit_sha: str,
        file_path: str,
        ast_hash: str,
        ast_data: str,
        grammar_version: str,
    ) -> None:
        """Upsert a cache entry.

        If an entry with the same ``(repo_path, commit_sha, file_path)``
        composite key already exists, all fields are updated.

        Args:
            repo_path: Absolute path to the repository root.
            commit_sha: Full 40-character commit SHA.
            file_path: Repository-relative file path.
            ast_hash: Hash of the AST content.
            ast_data: Serialised AST content (e.g. JSON string).
            grammar_version: Version tag of the tree-sitter grammar used.

        Raises:
            CacheError: On database write failure.
        """
        now = datetime.now(timezone.utc).isoformat()
        try:
            self._conn.execute(
                "INSERT INTO cache_entries "
                "(repo_path, commit_sha, file_path, ast_hash, ast_data, "
                "grammar_version, timestamp) "
                "VALUES (?, ?, ?, ?, ?, ?, ?) "
                "ON CONFLICT (repo_path, commit_sha, file_path) "
                "DO UPDATE SET "
                "  ast_hash        = excluded.ast_hash, "
                "  ast_data        = excluded.ast_data, "
                "  grammar_version = excluded.grammar_version, "
                "  timestamp       = excluded.timestamp",
                (repo_path, commit_sha, file_path, ast_hash, ast_data,
                 grammar_version, now),
            )
            self._conn.commit()
        except sqlite3.Error as exc:
            raise CacheError(f"Cache put failed: {exc}") from exc

    def is_cached(self, repo_path: str, commit_sha: str, file_path: str) -> bool:
        """Check whether an entry exists in the cache.

        Args:
            repo_path: Absolute path to the repository root.
            commit_sha: Full 40-character commit SHA.
            file_path: Repository-relative file path.

        Returns:
            ``True`` if a matching entry exists, ``False`` otherwise.

        Raises:
            CacheError: On database query failure.
        """
        try:
            cursor = self._conn.execute(
                "SELECT 1 FROM cache_entries "
                "WHERE repo_path = ? AND commit_sha = ? AND file_path = ?",
                (repo_path, commit_sha, file_path),
            )
            return cursor.fetchone() is not None
        except sqlite3.Error as exc:
            raise CacheError(f"Cache is_cached failed: {exc}") from exc

    def invalidate_grammar_version(self, old_version: str) -> int:
        """Delete all cache entries matching a grammar version.

        Called when a tree-sitter grammar is upgraded so stale cached ASTs
        are not reused.

        Args:
            old_version: Grammar version string to match.

        Returns:
            Number of deleted rows.

        Raises:
            CacheError: On database write failure.
        """
        try:
            cursor = self._conn.execute(
                "DELETE FROM cache_entries WHERE grammar_version = ?",
                (old_version,),
            )
            self._conn.commit()
            return cursor.rowcount
        except sqlite3.Error as exc:
            raise CacheError(
                f"Cache invalidate_grammar_version failed: {exc}"
            ) from exc

    def close(self) -> None:
        """Close the database connection.

        Idempotent — calling ``close()`` multiple times is safe.
        """
        if self._conn is not None:
            try:
                self._conn.close()
            except sqlite3.Error:
                pass
            self._conn = None  # type: ignore[assignment]
