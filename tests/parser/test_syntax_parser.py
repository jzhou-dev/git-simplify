"""Tests for the Tree-sitter syntax parser."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from git_simplify.parser import (
    SyntaxParser,
    TreeSitterManager,
    UnsupportedLanguageError,
)


class SyntaxParserTests(unittest.TestCase):
    def setUp(self) -> None:
        self.parser = SyntaxParser()

    def test_parses_python_source(self) -> None:
        result = self.parser.parse(
            "def greet(name):\n    return f'Hello, {name}'\n",
            "python",
        )

        self.assertEqual(result.language, "python")
        self.assertEqual(result.root_node.type, "module")
        self.assertFalse(result.has_errors)

    def test_reports_syntax_errors(self) -> None:
        result = self.parser.parse("def broken(:\n    pass\n", "python")

        self.assertTrue(result.has_errors)

    def test_parses_file_contents(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            file_path = Path(temporary_directory) / "example.py"
            file_path.write_text("value = 42\n", encoding="utf-8")

            result = self.parser.parse_file(file_path, "python")

        self.assertEqual(result.source, b"value = 42\n")
        self.assertEqual(result.root_node.type, "module")
        self.assertFalse(result.has_errors)

    def test_rejects_unsupported_language(self) -> None:
        with self.assertRaises(UnsupportedLanguageError):
            self.parser.parse("some source", "not-a-language")


class TreeSitterManagerTests(unittest.TestCase):
    def test_caches_loaded_languages(self) -> None:
        manager = TreeSitterManager()

        first_language = manager.get_language("python")
        second_language = manager.get_language("PYTHON")

        self.assertIs(first_language, second_language)


if __name__ == "__main__":
    unittest.main()
