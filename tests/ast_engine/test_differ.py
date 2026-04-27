"""Tests for driftscope.ast_engine.differ."""

from unittest.mock import MagicMock, patch

import pytest

from driftscope.ast_engine.differ import (
    _diff_nodes,
    _walk_tree,
    compute_ast_diff,
)
from driftscope.ast_engine.parser import compute_text_hash
from driftscope.models.ast_diff import ASTFileDiff


# ---------------------------------------------------------------------------
# _walk_tree
# ---------------------------------------------------------------------------


class TestWalkTree:
    """Tests for _walk_tree."""

    def test_walks_named_nodes(self) -> None:
        """_walk_tree must collect all named nodes from the tree."""
        # Build a fake tree-sitter tree:
        # root (named) -> child_a (named), child_b (unnamed)
        child_a = MagicMock()
        child_a.is_named = True
        child_a.type = "identifier"
        child_a.text = b"foo"
        child_a.start_point = (0, 0)
        child_a.end_point = (0, 3)
        child_a.children = []

        child_b = MagicMock()
        child_b.is_named = False
        child_b.children = []

        root = MagicMock()
        root.is_named = True
        root.type = "module"
        root.text = b"foo"
        root.start_point = (0, 0)
        root.end_point = (0, 3)
        root.children = [child_a, child_b]

        tree = MagicMock()
        tree.root_node = root

        nodes = _walk_tree(tree)
        # root and child_a are named; child_b is not
        assert len(nodes) == 2
        assert nodes[0]["node_type"] == "module"
        assert nodes[1]["node_type"] == "identifier"

    def test_empty_tree(self) -> None:
        """A tree with only unnamed nodes must produce an empty list."""
        root = MagicMock()
        root.is_named = False
        root.children = []

        tree = MagicMock()
        tree.root_node = root

        nodes = _walk_tree(tree)
        assert nodes == []


# ---------------------------------------------------------------------------
# _diff_nodes
# ---------------------------------------------------------------------------


class TestDiffNodes:
    """Tests for _diff_nodes."""

    def test_no_changes(self) -> None:
        """Identical node sets must produce no changes."""
        nodes = [
            {
                "node_type": "identifier",
                "start_line": 1,
                "end_line": 1,
                "text": "x",
                "text_hash": compute_text_hash("x"),
            },
        ]
        changes = _diff_nodes(nodes, nodes)
        assert len(changes) == 0

    def test_added_nodes(self) -> None:
        """Nodes present in after but not before are 'added'."""
        before: list[dict] = []
        after = [
            {
                "node_type": "function_definition",
                "start_line": 1,
                "end_line": 3,
                "text": "def foo(): pass",
                "text_hash": compute_text_hash("def foo(): pass"),
            },
        ]
        changes = _diff_nodes(before, after)
        assert len(changes) == 1
        assert changes[0].change_type == "added"
        assert changes[0].node_type == "function_definition"

    def test_removed_nodes(self) -> None:
        """Nodes present in before but not after are 'removed'."""
        before = [
            {
                "node_type": "expression_statement",
                "start_line": 1,
                "end_line": 1,
                "text": "x = 1",
                "text_hash": compute_text_hash("x = 1"),
            },
        ]
        after: list[dict] = []
        changes = _diff_nodes(before, after)
        assert len(changes) == 1
        assert changes[0].change_type == "removed"

    def test_mixed_additions_and_removals(self) -> None:
        """Both additions and removals in a single diff."""
        before = [
            {
                "node_type": "identifier",
                "start_line": 1,
                "end_line": 1,
                "text": "old_var",
                "text_hash": compute_text_hash("old_var"),
            },
        ]
        after = [
            {
                "node_type": "identifier",
                "start_line": 1,
                "end_line": 1,
                "text": "new_var",
                "text_hash": compute_text_hash("new_var"),
            },
        ]
        changes = _diff_nodes(before, after)
        types = {c.change_type for c in changes}
        assert types == {"added", "removed"}


# ---------------------------------------------------------------------------
# compute_ast_diff
# ---------------------------------------------------------------------------


class TestComputeAstDiff:
    """Tests for compute_ast_diff with mocked parsing."""

    @patch("driftscope.ast_engine.differ.parse_source")
    def test_returns_ast_file_diff(self, mock_parse: MagicMock) -> None:
        """compute_ast_diff must return a valid ASTFileDiff."""
        # Build fake trees with simple named nodes
        before_node = MagicMock()
        before_node.is_named = True
        before_node.type = "identifier"
        before_node.text = b"x"
        before_node.start_point = (0, 0)
        before_node.end_point = (0, 1)
        before_node.children = []

        before_root = MagicMock()
        before_root.is_named = True
        before_root.type = "module"
        before_root.text = b"x"
        before_root.start_point = (0, 0)
        before_root.end_point = (0, 1)
        before_root.children = [before_node]

        before_tree = MagicMock()
        before_tree.root_node = before_root

        # After tree has a different node (y instead of x)
        after_node = MagicMock()
        after_node.is_named = True
        after_node.type = "identifier"
        after_node.text = b"y"
        after_node.start_point = (0, 0)
        after_node.end_point = (0, 1)
        after_node.children = []

        after_root = MagicMock()
        after_root.is_named = True
        after_root.type = "module"
        after_root.text = b"y"
        after_root.start_point = (0, 0)
        after_root.end_point = (0, 1)
        after_root.children = [after_node]

        after_tree = MagicMock()
        after_tree.root_node = after_root

        mock_parse.side_effect = [before_tree, after_tree]

        result = compute_ast_diff(
            before="x",
            after="y",
            language="python",
            commit_sha="a" * 40,
            file_path="test.py",
            authorship_class="human",
        )
        assert isinstance(result, ASTFileDiff)
        assert result.commit_sha == "a" * 40
        assert result.authorship_class == "human"
        assert len(result.changes) > 0

    @patch("driftscope.ast_engine.differ.parse_source")
    def test_identical_sources_no_changes(self, mock_parse: MagicMock) -> None:
        """Identical before/after sources must produce zero changes."""
        node = MagicMock()
        node.is_named = True
        node.type = "identifier"
        node.text = b"x"
        node.start_point = (0, 0)
        node.end_point = (0, 1)
        node.children = []

        root = MagicMock()
        root.is_named = True
        root.type = "module"
        root.text = b"x"
        root.start_point = (0, 0)
        root.end_point = (0, 1)
        root.children = [node]

        tree = MagicMock()
        tree.root_node = root

        mock_parse.side_effect = [tree, tree]

        result = compute_ast_diff(
            before="x",
            after="x",
            language="python",
            commit_sha="b" * 40,
            file_path="same.py",
            authorship_class="ai",
        )
        assert len(result.changes) == 0
        assert result.authorship_class == "ai"
