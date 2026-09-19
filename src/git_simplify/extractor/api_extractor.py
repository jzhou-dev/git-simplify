"""Extract common web API route declarations."""

from __future__ import annotations

from dataclasses import dataclass
import re

from tree_sitter import Node

from ..parser.syntax_parser import ParseResult
from ._tree_utils import location, text, walk


@dataclass(frozen=True)
class ApiDefinition:
    """A route-like API declaration found in source code."""

    name: str
    method: str
    path: str
    start_line: int
    start_column: int
    end_line: int
    end_column: int


ROUTE_PATTERN = re.compile(
    r"(?:app|api|router)\.(get|post|put|patch|delete|options|head)"
    r"\s*\(\s*[\"']([^\"']+)[\"']",
    re.IGNORECASE,
)
DECORATOR_PATTERN = re.compile(
    r"(?:get|post|put|patch|delete|options|head)"
    r"\s*\(\s*[\"']([^\"']+)[\"']",
    re.IGNORECASE,
)


class ApiExtractor:
    """Extract route decorators and common Express-style route calls."""

    def extract(self, result: ParseResult) -> list[ApiDefinition]:
        apis: list[ApiDefinition] = []
        for node in walk(result.root_node):
            if node.type not in {"call", "call_expression"}:
                if node.type not in {"decorator", "decorator_definition"}:
                    continue

            node_text = text(node, result.source)
            match = ROUTE_PATTERN.search(node_text)
            if match:
                apis.append(self._api(node, match.group(1), match.group(2)))
                continue

            if node.type not in {"decorator", "decorator_definition"}:
                continue
            match = DECORATOR_PATTERN.search(node_text)
            if match:
                method = node_text.lstrip("@").split("(", 1)[0].split(".")[-1]
                apis.append(self._api(node, method, match.group(1)))
        return apis

    @staticmethod
    def _api(node: Node, method: str, path: str) -> ApiDefinition:
        start_line, start_column, end_line, end_column = location(node)
        name = f"{method.upper()} {path}"
        return ApiDefinition(
            name=name,
            method=method.upper(),
            path=path,
            start_line=start_line,
            start_column=start_column,
            end_line=end_line,
            end_column=end_column,
        )
