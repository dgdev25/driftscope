"""AST diff computation via tree-sitter tree walking.

Walks two tree-sitter parse trees, collects named nodes, and computes
added/removed/modified changes by comparing text hashes.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from driftscope.ast_engine.parser import compute_text_hash, parse_source
from driftscope.models.ast_diff import ASTFileDiff, ASTNodeChange


def _walk_tree(tree: object) -> list[dict[str, object]]:
    """Recursively walk a tree-sitter Tree and collect named nodes.

    Args:
        tree: A ``tree_sitter.Tree`` instance.

    Returns:
        List of dicts with keys:
            - node_type: str
            - start_line: int (1-based)
            - end_line: int (1-based)
            - text: str
            - text_hash: str

    Time Complexity: O(n) where n = number of tree nodes
    Space Complexity: O(m) where m = number of named nodes
    """
    root = tree.root_node
    nodes: list[dict[str, object]] = []
    _walk_node(root, nodes)
    return nodes


def _walk_node(node: object, accumulator: list[dict[str, object]]) -> None:
    """Recursively visit a node and its children, collecting named nodes."""
    if node.is_named:
        text = node.text
        if isinstance(text, bytes):
            text = text.decode("utf-8")
        start_byte = node.start_point
        end_byte = node.end_point
        start_line = start_byte[0] + 1  # Convert 0-based to 1-based
        end_line = end_byte[0] + 1
        accumulator.append({
            "node_type": node.type,
            "start_line": start_line,
            "end_line": end_line,
            "text": text,
            "text_hash": compute_text_hash(text),
        })
    for child in node.children:
        _walk_node(child, accumulator)


def _diff_nodes(
    before_nodes: list[dict[str, object]],
    after_nodes: list[dict[str, object]],
) -> list[ASTNodeChange]:
    """Compare two sets of walked nodes and produce change records.

    Uses text_hash set difference to determine added and removed nodes.

    Args:
        before_nodes: Walked nodes from the "before" tree.
        after_nodes: Walked nodes from the "after" tree.

    Returns:
        List of ASTNodeChange records with change_type "added" or "removed".

    Time Complexity: O(n + m) where n = len(before_nodes), m = len(after_nodes)
    Space Complexity: O(n + m)
    """
    before_hashes = {n["text_hash"]: n for n in before_nodes}
    after_hashes = {n["text_hash"]: n for n in after_nodes}

    changes: list[ASTNodeChange] = []

    removed_hashes = set(before_hashes.keys()) - set(after_hashes.keys())
    for h in sorted(removed_hashes):
        node = before_hashes[h]
        changes.append(ASTNodeChange(
            node_type=node["node_type"],
            start_line=node["start_line"],
            end_line=node["end_line"],
            change_type="removed",
            text_hash=h,
        ))

    added_hashes = set(after_hashes.keys()) - set(before_hashes.keys())
    for h in sorted(added_hashes):
        node = after_hashes[h]
        changes.append(ASTNodeChange(
            node_type=node["node_type"],
            start_line=node["start_line"],
            end_line=node["end_line"],
            change_type="added",
            text_hash=h,
        ))

    return changes


def compute_ast_diff(
    before: str,
    after: str,
    language: str,
    commit_sha: str,
    file_path: str | Path,
    authorship_class: Literal["human", "ai"],
) -> ASTFileDiff:
    """Compute the AST diff between two versions of a source file.

    Args:
        before: Source code text of the file before the commit.
        after: Source code text of the file after the commit.
        language: Language identifier for tree-sitter parsing.
        commit_sha: 40-character hex SHA of the commit.
        file_path: Path of the file being diffed.
        authorship_class: Whether this commit is attributed to "human" or "ai".

    Returns:
        ASTFileDiff with individual node changes.

    Raises:
        ASTParseError: If parsing fails for either side.
    """
    before_tree = parse_source(before, language)
    after_tree = parse_source(after, language)

    before_nodes = _walk_tree(before_tree)
    after_nodes = _walk_tree(after_tree)

    changes = _diff_nodes(before_nodes, after_nodes)

    before_hash = compute_text_hash(before) if before else None
    after_hash = compute_text_hash(after) if after else None

    return ASTFileDiff(
        file_path=Path(file_path),
        commit_sha=commit_sha,
        before_hash=before_hash,
        after_hash=after_hash,
        changes=changes,
        authorship_class=authorship_class,
    )
