"""Tests for the ProvenanceEntry model."""

from datetime import datetime, timezone

from driftscope.models.provenance import ProvenanceEntry


def test_provenance_entry_ai() -> None:
    entry = ProvenanceEntry(
        file_path="src/payments/processor.py",
        line_start=45,
        line_end=67,
        authorship_class="ai",
        originating_commit_sha="a" * 40,
        commit_timestamp=datetime(2025, 11, 14, 9, 23, 0, tzinfo=timezone.utc),
        co_authorship_tag="Co-Authored-By: Claude",
    )
    assert entry.authorship_class == "ai"
    assert entry.co_authorship_tag == "Co-Authored-By: Claude"


def test_provenance_entry_human() -> None:
    entry = ProvenanceEntry(
        file_path="src/auth/login.py",
        line_start=10,
        line_end=20,
        authorship_class="human",
        originating_commit_sha="f" * 40,
        commit_timestamp=datetime(2025, 10, 30, 14, 17, 0, tzinfo=timezone.utc),
    )
    assert entry.co_authorship_tag is None


def test_provenance_entry_json_round_trip() -> None:
    entry = ProvenanceEntry(
        file_path="src/main.py",
        line_start=1,
        line_end=5,
        authorship_class="human",
        originating_commit_sha="b" * 40,
        commit_timestamp=datetime(2025, 6, 1, tzinfo=timezone.utc),
    )
    json_str = entry.model_dump_json()
    restored = ProvenanceEntry.model_validate_json(json_str)
    assert restored.file_path == entry.file_path
    assert restored.line_start == entry.line_start
