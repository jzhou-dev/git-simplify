"""Extract declarations for functions, classes, methods, and variables."""

from __future__ import annotations

from dataclasses import dataclass

from tree_sitter import Node

from ..parser.syntax_parser import ParseResult
from ._tree_utils import location, named_field_text, text, walk


@dataclass(frozen=True)
class Symbol:
    """A named declaration found in a source file."""

    name: str
    kind: str
    start_line: int
    start_column: int
    end_line: int
    end_column: int


SYMBOL_KINDS = {
    "function_definition": "function",
    "function_declaration": "function",
    "generator_function_declaration": "function",
    "class_definition": "class",
    "class_declaration": "class",
    "method_definition": "method",
    "interface_declaration": "interface",
    "type_alias_declaration": "type",
    "enum_declaration": "enum",
    "variable_declarator": "variable",
}


class SymbolExtractor:
    """Extract named declarations using common Tree-sitter node types."""

    def extract(self, result: ParseResult) -> list[Symbol]:
        symbols: list[Symbol] = []
        for node in walk(result.root_node):
            kind = SYMBOL_KINDS.get(node.type)
            if kind is None:
                continue

            name = self._name(node, result.source)
            if not name:
                continue

            start_line, start_column, end_line, end_column = location(node)
            symbols.append(
                Symbol(
                    name=name,
                    kind=kind,
                    start_line=start_line,
                    start_column=start_column,
                    end_line=end_line,
                    end_column=end_column,
                )
            )
        return symbols

    @staticmethod
    def _name(node: Node, source: bytes) -> str | None:
        name = named_field_text(node, "name", source)
        if name:
            return name

        for child in node.named_children:
            if child.type in {"identifier", "property_identifier", "type_identifier"}:
                return text(child, source)
        return None
