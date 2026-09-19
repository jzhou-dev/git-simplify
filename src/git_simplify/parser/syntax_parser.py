"""Parse source text into Tree-sitter syntax trees."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from tree_sitter import Node, Tree

from .tree_sitter_manager import TreeSitterManager


@dataclass(frozen=True)
class ParseResult:
    """The result of parsing one source document."""

    tree: Tree
    language: str
    source: bytes

    @property
    def root_node(self) -> Node:
        """Return the root node of the parsed syntax tree."""
        return self.tree.root_node

    @property
    def has_errors(self) -> bool:
        """Return whether Tree-sitter encountered syntax errors."""
        return self.root_node.has_error


class SyntaxParser:
    """Parse source text or files with Tree-sitter."""

    def __init__(self, manager: TreeSitterManager | None = None) -> None:
        self.manager = manager or TreeSitterManager()

    def parse(self, source: str | bytes, language: str) -> ParseResult:
        """Parse source text using the grammar for ``language``."""
        source_bytes = source.encode("utf-8") if isinstance(source, str) else source
        parser = self.manager.create_parser(language)
        tree = parser.parse(source_bytes)
        return ParseResult(tree=tree, language=language.lower(), source=source_bytes)

    def parse_file(self, file_path: str | Path, language: str) -> ParseResult:
        """Read and parse a source file."""
        source = Path(file_path).read_bytes()
        return self.parse(source, language)
