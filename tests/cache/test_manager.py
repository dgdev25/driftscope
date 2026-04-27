"""Tests for CacheManager — SQLite-backed incremental AST analysis cache."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from driftscope.cache.manager import CacheError, CacheManager


# ---------------------------------------------------------------------------
# Fixture
# ---------------------------------------------------------------------------


@pytest.fixture()
def cache(tmp_path: Path) -> CacheManager:
    """Return a CacheManager backed by a temp directory."""
    db_path = tmp_path / "sub" / "dir" / "cache.db"
    mgr = CacheManager(db_path)
    yield mgr
    mgr.close()


# ===========================================================================
# put / get round-trip
# ===========================================================================


def test_put_get_round_trip(cache: CacheManager) -> None:
    """Storing and retrieving an entry returns the original ast_data."""
    cache.put(
        repo_path="/repo",
        commit_sha="abc123",
        file_path="src/main.py",
        ast_hash="h1",
        ast_data='{"node": "module"}',
        grammar_version="0.22.0",
    )
    result = cache.get("/repo", "abc123", "src/main.py")
    assert result == '{"node": "module"}'


# ===========================================================================
# get missing key returns None
# ===========================================================================


def test_get_missing_returns_none(cache: CacheManager) -> None:
    """Querying a key that was never stored returns None."""
    assert cache.get("/no/repo", "deadbeef", "gone.py") is None


# ===========================================================================
# multiple entries are independent
# ===========================================================================


def test_multiple_entries_independent(cache: CacheManager) -> None:
    """Multiple entries coexist and do not interfere."""
    cache.put("/r", "c1", "a.py", "h1", "data_a", "1.0")
    cache.put("/r", "c2", "b.py", "h2", "data_b", "1.0")
    cache.put("/r", "c1", "c.py", "h3", "data_c", "1.0")

    assert cache.get("/r", "c1", "a.py") == "data_a"
    assert cache.get("/r", "c2", "b.py") == "data_b"
    assert cache.get("/r", "c1", "c.py") == "data_c"


# ===========================================================================
# overwrite returns latest value
# ===========================================================================


def test_overwrite_returns_latest(cache: CacheManager) -> None:
    """Upserting the same composite key overwrites ast_data."""
    cache.put("/r", "c1", "a.py", "h1", "old_data", "1.0")
    cache.put("/r", "c1", "a.py", "h2", "new_data", "1.0")

    assert cache.get("/r", "c1", "a.py") == "new_data"


# ===========================================================================
# overwrite updates ast_hash and grammar_version
# ===========================================================================


def test_overwrite_updates_ast_hash_and_grammar(cache: CacheManager) -> None:
    """Upsert updates ast_hash and grammar_version (verified via invalidate)."""
    cache.put("/r", "c1", "a.py", "h1", "data", "1.0")
    # Overwrite with new grammar version
    cache.put("/r", "c1", "a.py", "h2", "data_v2", "2.0")

    # Old version should have no entries left
    assert cache.invalidate_grammar_version("1.0") == 0
    # Entry still exists with new version
    assert cache.get("/r", "c1", "a.py") == "data_v2"


# ===========================================================================
# is_cached
# ===========================================================================


def test_is_cached_true_after_put(cache: CacheManager) -> None:
    """is_cached returns True after an entry is stored."""
    cache.put("/r", "c1", "a.py", "h1", "data", "1.0")
    assert cache.is_cached("/r", "c1", "a.py") is True


def test_is_cached_false_without_put(cache: CacheManager) -> None:
    """is_cached returns False when no entry exists."""
    assert cache.is_cached("/r", "c1", "a.py") is False


def test_is_cached_false_after_invalidation(cache: CacheManager) -> None:
    """is_cached returns False after the entry's grammar version is invalidated."""
    cache.put("/r", "c1", "a.py", "h1", "data", "1.0")
    cache.invalidate_grammar_version("1.0")
    assert cache.is_cached("/r", "c1", "a.py") is False


# ===========================================================================
# invalidate_grammar_version
# ===========================================================================


def test_invalidate_removes_matching_preserves_others(cache: CacheManager) -> None:
    """invalidate_grammar_version deletes only matching entries."""
    cache.put("/r", "c1", "a.py", "h1", "data_a", "1.0")
    cache.put("/r", "c1", "b.py", "h2", "data_b", "2.0")
    cache.put("/r", "c1", "c.py", "h3", "data_c", "1.0")

    removed = cache.invalidate_grammar_version("1.0")
    assert removed == 2

    assert cache.get("/r", "c1", "a.py") is None
    assert cache.get("/r", "c1", "c.py") is None
    # Different grammar version preserved
    assert cache.get("/r", "c1", "b.py") == "data_b"


def test_invalidate_no_match_returns_zero(cache: CacheManager) -> None:
    """invalidate_grammar_version returns 0 when nothing matches."""
    cache.put("/r", "c1", "a.py", "h1", "data", "1.0")
    assert cache.invalidate_grammar_version("9.9") == 0
    # Original entry still present
    assert cache.get("/r", "c1", "a.py") == "data"


# ===========================================================================
# directory / file creation
# ===========================================================================


def test_creates_nested_directories(tmp_path: Path) -> None:
    """CacheManager creates intermediate directories for the DB path."""
    db_path = tmp_path / "a" / "b" / "c" / "cache.db"
    mgr = CacheManager(db_path)
    try:
        assert db_path.parent.is_dir()
        # put should succeed without errors
        mgr.put("/r", "c1", "f.py", "h", "d", "1.0")
    finally:
        mgr.close()


def test_existing_directory_ok(tmp_path: Path) -> None:
    """CacheManager works when the parent directory already exists."""
    db_path = tmp_path / "cache.db"
    # Pre-create directory
    db_path.parent.mkdir(parents=True, exist_ok=True)
    mgr = CacheManager(db_path)
    try:
        mgr.put("/r", "c1", "f.py", "h", "d", "1.0")
        assert mgr.get("/r", "c1", "f.py") == "d"
    finally:
        mgr.close()


# ===========================================================================
# close is idempotent
# ===========================================================================


def test_close_idempotent(cache: CacheManager) -> None:
    """Calling close() multiple times does not raise."""
    cache.close()
    cache.close()
    cache.close()


# ===========================================================================
# CacheError on directory creation failure
# ===========================================================================


def test_cache_error_on_mkdir_failure(tmp_path: Path) -> None:
    """CacheError is raised when the DB parent directory cannot be created."""
    db_path = tmp_path / "readonly" / "cache.db"
    with patch.object(Path, "mkdir", side_effect=OSError("permission denied")):
        with pytest.raises(CacheError, match="permission denied"):
            CacheManager(db_path)


# ===========================================================================
# CacheError on sqlite3 failures
# ===========================================================================


def test_cache_error_on_connect_failure(tmp_path: Path) -> None:
    """CacheError is raised when sqlite3.connect fails."""
    db_path = tmp_path / "cache.db"
    with patch("driftscope.cache.manager.sqlite3.connect") as mock_connect:
        mock_connect.side_effect = sqlite3.Error("disk error")
        with pytest.raises(CacheError, match="Cannot open cache database"):
            CacheManager(db_path)


def test_get_raises_cache_error_on_db_failure(cache: CacheManager) -> None:
    """CacheError is raised when the underlying SELECT fails."""
    with patch.object(cache, "_conn") as mock_conn:
        mock_conn.execute.side_effect = sqlite3.Error("corrupt")
        with pytest.raises(CacheError, match="Cache get failed"):
            cache.get("/r", "c1", "f.py")


def test_put_raises_cache_error_on_db_failure(cache: CacheManager) -> None:
    """CacheError is raised when the underlying INSERT fails."""
    with patch.object(cache, "_conn") as mock_conn:
        mock_conn.execute.side_effect = sqlite3.Error("disk full")
        with pytest.raises(CacheError, match="Cache put failed"):
            cache.put("/r", "c1", "f.py", "h", "d", "1.0")


def test_is_cached_raises_cache_error_on_db_failure(cache: CacheManager) -> None:
    """CacheError is raised when the underlying SELECT fails."""
    with patch.object(cache, "_conn") as mock_conn:
        mock_conn.execute.side_effect = sqlite3.Error("locked")
        with pytest.raises(CacheError, match="Cache is_cached failed"):
            cache.is_cached("/r", "c1", "f.py")


def test_invalidate_raises_cache_error_on_db_failure(cache: CacheManager) -> None:
    """CacheError is raised when the underlying DELETE fails."""
    with patch.object(cache, "_conn") as mock_conn:
        mock_conn.execute.side_effect = sqlite3.Error("readonly")
        with pytest.raises(CacheError, match="Cache invalidate_grammar_version failed"):
            cache.invalidate_grammar_version("1.0")


def test_close_handles_sqlite_error(tmp_path: Path) -> None:
    """close() swallows sqlite3.Error without raising."""
    db_path = tmp_path / "cache.db"
    mgr = CacheManager(db_path)
    # Close the real connection first, then replace with a mock
    mgr._conn.close()
    mock_conn = MagicMock()
    mock_conn.close.side_effect = sqlite3.Error("busy")
    mgr._conn = mock_conn
    # Should not raise despite the inner error
    mgr.close()
    assert mgr._conn is None
