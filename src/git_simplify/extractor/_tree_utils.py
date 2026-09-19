"""Small helpers shared by Tree-sitter extractors."""

from __future__ import annotations

from collections.abc import Iterator

from tree_sitter import Node


def walk(node: Node) -> Iterator[Node]:
    """Yield ``node`` and every descendant in depth-first order."""
    yield node
    for child in node.named_children:
        yield from walk(child)


def text(node: Node, source: bytes) -> str:
    """Return a node's source text as a decoded string."""
    return source[node.start_byte : node.end_byte].decode("utf-8", errors="replace")


def named_field_text(node: Node, field_name: str, source: bytes) -> str | None:
    """Return decoded text for a named field when it exists."""
    field = node.child_by_field_name(field_name)
    return text(field, source) if field is not None else None


def location(node: Node) -> tuple[int, int, int, int]:
    """Return a node location as zero-based start/end line and column values."""
    return (
        node.start_point[0],
        node.start_point[1],
        node.end_point[0],
        node.end_point[1],
    )
