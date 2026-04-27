"""Tests for driftscope.git_client.diff_parser."""

from driftscope.git_client.diff_parser import FileHunk, parse_unified_diff


class TestFileHunk:
    """Tests for FileHunk dataclass."""

    def test_file_hunk_creation(self) -> None:
        hunk = FileHunk(
            file_path="src/main.py",
            added_lines=[10, 11, 12],
            removed_lines=[5, 6],
        )
        assert hunk.file_path == "src/main.py"
        assert hunk.added_lines == [10, 11, 12]
        assert hunk.removed_lines == [5, 6]

    def test_file_hunk_frozen(self) -> None:
        hunk = FileHunk(file_path="a.py", added_lines=[], removed_lines=[])
        try:
            hunk.file_path = "b.py"  # type: ignore[misc]
            assert False, "Should raise FrozenInstanceError"
        except AttributeError:
            pass

    def test_file_hunk_default_empty_lists(self) -> None:
        """FileHunk requires explicit lists, no default mutation risk."""
        hunk = FileHunk(file_path="x.py", added_lines=[], removed_lines=[])
        assert hunk.added_lines == []
        assert hunk.removed_lines == []


class TestParseUnifiedDiff:
    """Tests for parse_unified_diff function."""

    def test_empty_diff(self) -> None:
        result = parse_unified_diff("")
        assert result == []

    def test_simple_addition(self) -> None:
        diff = (
            "diff --git a/main.py b/main.py\n"
            "index abc1234..def5678 100644\n"
            "--- a/main.py\n"
            "+++ b/main.py\n"
            "@@ -1,2 +1,3 @@\n"
            " line1\n"
            " line2\n"
            "+line3\n"
        )
        result = parse_unified_diff(diff)
        assert len(result) == 1
        assert result[0].file_path == "main.py"
        assert result[0].added_lines == [3]
        assert result[0].removed_lines == []

    def test_simple_deletion(self) -> None:
        diff = (
            "diff --git a/app.py b/app.py\n"
            "--- a/app.py\n"
            "+++ b/app.py\n"
            "@@ -1,3 +1,2 @@\n"
            " line1\n"
            "-line2\n"
            " line3\n"
        )
        result = parse_unified_diff(diff)
        assert len(result) == 1
        assert result[0].file_path == "app.py"
        assert result[0].added_lines == []
        assert result[0].removed_lines == [2]

    def test_mixed_add_remove(self) -> None:
        diff = (
            "diff --git a/util.py b/util.py\n"
            "--- a/util.py\n"
            "+++ b/util.py\n"
            "@@ -5,5 +5,5 @@\n"
            " ctx1\n"
            "-old_line\n"
            "+new_line\n"
            " ctx2\n"
        )
        result = parse_unified_diff(diff)
        assert len(result) == 1
        assert result[0].file_path == "util.py"
        assert result[0].removed_lines == [6]
        assert result[0].added_lines == [6]

    def test_multiple_hunks_same_file(self) -> None:
        diff = (
            "diff --git a/big.py b/big.py\n"
            "--- a/big.py\n"
            "+++ b/big.py\n"
            "@@ -1,3 +1,4 @@\n"
            " a\n"
            "+b\n"
            " c\n"
            "@@ -20,3 +21,3 @@\n"
            " d\n"
            "-e\n"
            "+f\n"
            " g\n"
        )
        result = parse_unified_diff(diff)
        assert len(result) == 1
        assert result[0].file_path == "big.py"
        assert result[0].added_lines == [2, 22]
        assert result[0].removed_lines == [21]

    def test_multiple_files(self) -> None:
        diff = (
            "diff --git a/a.py b/a.py\n"
            "--- a/a.py\n"
            "+++ b/a.py\n"
            "@@ -1,2 +1,3 @@\n"
            " x\n"
            "+y\n"
            " z\n"
            "diff --git a/b.py b/b.py\n"
            "--- a/b.py\n"
            "+++ b/b.py\n"
            "@@ -10,2 +10,1 @@\n"
            " p\n"
            "-q\n"
        )
        result = parse_unified_diff(diff)
        assert len(result) == 2
        assert result[0].file_path == "a.py"
        assert result[0].added_lines == [2]
        assert result[1].file_path == "b.py"
        assert result[1].removed_lines == [11]

    def test_hunk_header_with_zero_count(self) -> None:
        """A hunk with count=0 means the file was purely added or removed."""
        diff = (
            "diff --git a/new.py b/new.py\n"
            "--- /dev/null\n"
            "+++ b/new.py\n"
            "@@ -0,0 +1,2 @@\n"
            "+line1\n"
            "+line2\n"
        )
        result = parse_unified_diff(diff)
        assert len(result) == 1
        assert result[0].file_path == "new.py"
        assert result[0].added_lines == [1, 2]
        assert result[0].removed_lines == []
