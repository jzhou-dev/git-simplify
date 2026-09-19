"""Extract function, method, and constructor calls from syntax trees."""

from __future__ import annotations

from dataclasses import dataclass

from tree_sitter import Node

from ..parser.syntax_parser import ParseResult
from ._tree_utils import location, named_field_text, walk


@dataclass(frozen=True)
class CallReference:
    """A call expression found in a source file."""

    function: str
    arguments_count: int | None
    kind: str
    start_line: int
    start_column: int
    end_line: int
    end_column: int


CALL_NODE_TYPES = {"call", "call_expression", "new_expression"}


class CallExtractor:
    """Extract call expressions from common Tree-sitter grammars."""

    def extract(self, result: ParseResult) -> list[CallReference]:
        calls: list[CallReference] = []
        for node in walk(result.root_node):
            if node.type not in CALL_NODE_TYPES:
                continue

            function = (
                named_field_text(node, "function", result.source)
                or named_field_text(node, "constructor", result.source)
            )
            if not function:
                continue

            arguments = node.child_by_field_name("arguments")
            arguments_count = len(arguments.named_children) if arguments else None
            start_line, start_column, end_line, end_column = location(node)
            calls.append(
                CallReference(
                    function=function,
                    arguments_count=arguments_count,
                    kind="constructor" if node.type == "new_expression" else "call",
                    start_line=start_line,
                    start_column=start_column,
                    end_line=end_line,
                    end_column=end_column,
                )
            )
        return calls
