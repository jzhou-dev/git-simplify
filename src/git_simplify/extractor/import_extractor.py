"""Extract import and export declarations from syntax trees."""

from __future__ import annotations

from dataclasses import dataclass
import re

from tree_sitter import Node

from ..parser.syntax_parser import ParseResult
from ._tree_utils import location, text, walk


@dataclass(frozen=True)
class ImportReference:
    """An import or export reference found in a source file."""

    module: str
    name: str | None
    alias: str | None
    kind: str
    start_line: int
    start_column: int
    end_line: int
    end_column: int


IMPORT_NODE_TYPES = {
    "import_statement",
    "import_from_statement",
    "import_declaration",
}
EXPORT_NODE_TYPES = {"export_statement", "export_declaration"}


class ImportExtractor:
    """Extract common Python and JavaScript/TypeScript import forms."""

    def extract(self, result: ParseResult) -> list[ImportReference]:
        references: list[ImportReference] = []
        for node in walk(result.root_node):
            if node.type in IMPORT_NODE_TYPES:
                reference = self._parse_import(node, result.source)
                if reference is not None:
                    references.append(reference)
            elif node.type in EXPORT_NODE_TYPES:
                reference = self._parse_export(node, result.source)
                if reference is not None:
                    references.append(reference)
        return references

    def _parse_import(self, node: Node, source: bytes) -> ImportReference | None:
        statement = text(node, source).strip().rstrip(";")
        python_from_match = re.match(
            r"from\s+([^\s]+)\s+import\s+(.+)",
            statement,
        )
        if python_from_match:
            return self._reference(
                node,
                python_from_match.group(1),
                python_from_match.group(2).strip(),
                None,
                "import",
            )

        module_match = re.search(r"(?:from\s+)?[\"']([^\"']+)[\"']", statement)
        if module_match:
            module = module_match.group(1)
            imported_name = None
            alias = None
            if statement.startswith("from "):
                imported_name = statement.split("import", 1)[-1].strip() or None
            elif statement.startswith("import "):
                imported_name = statement.removeprefix("import ").split(" from ", 1)[0].strip()
            return self._reference(node, module, imported_name, alias, "import")

        if statement.startswith("import "):
            module = statement.removeprefix("import ").strip().split(",", 1)[0]
            return self._reference(node, module, None, None, "import")
        return None

    def _parse_export(self, node: Node, source: bytes) -> ImportReference | None:
        statement = text(node, source).strip().rstrip(";")
        module_match = re.search(r"from\s+[\"']([^\"']+)[\"']", statement)
        if module_match:
            return self._reference(node, module_match.group(1), None, None, "export")
        return None

    @staticmethod
    def _reference(
        node: Node,
        module: str,
        name: str | None,
        alias: str | None,
        kind: str,
    ) -> ImportReference:
        start_line, start_column, end_line, end_column = location(node)
        return ImportReference(
            module=module,
            name=name,
            alias=alias,
            kind=kind,
            start_line=start_line,
            start_column=start_column,
            end_line=end_line,
            end_column=end_column,
        )
