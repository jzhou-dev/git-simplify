"""Manage Tree-sitter languages and parser instances."""

from __future__ import annotations

from tree_sitter import Parser

from .language_grammars import load_language


class TreeSitterManager:
    """Load grammars once and create parsers for supported languages."""

    def __init__(self) -> None:
        self._languages = {}

    def get_language(self, language_name: str):
        """Return a cached Tree-sitter language object."""
        normalized_name = language_name.lower()
        if normalized_name not in self._languages:
            self._languages[normalized_name] = load_language(normalized_name)
        return self._languages[normalized_name]

    def create_parser(self, language_name: str) -> Parser:
        """Create a parser configured for ``language_name``."""
        parser = Parser()
        parser.language = self.get_language(language_name)
        return parser
