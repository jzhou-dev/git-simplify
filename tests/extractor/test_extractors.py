"""Tests for syntax-tree extractors."""

from __future__ import annotations

import unittest

from git_simplify.extractor import (
    ApiExtractor,
    CallExtractor,
    ImportExtractor,
    SymbolExtractor,
)
from git_simplify.parser import SyntaxParser


class ExtractorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.parser = SyntaxParser()

    def test_extracts_python_imports(self) -> None:
        result = self.parser.parse(
            "import os\nfrom pathlib import Path as FilePath\n",
            "python",
        )

        imports = ImportExtractor().extract(result)

        self.assertEqual(
            [(item.module, item.name) for item in imports],
            [("os", None), ("pathlib", "Path as FilePath")],
        )

    def test_extracts_python_symbols(self) -> None:
        result = self.parser.parse(
            "class Greeter:\n"
            "    def greet(self):\n"
            "        return 'hello'\n"
            "\n"
            "def build_greeter():\n"
            "    return Greeter()\n",
            "python",
        )

        symbols = SymbolExtractor().extract(result)

        self.assertEqual(
            [(symbol.name, symbol.kind) for symbol in symbols],
            [
                ("Greeter", "class"),
                ("greet", "function"),
                ("build_greeter", "function"),
            ],
        )

    def test_extracts_python_calls(self) -> None:
        result = self.parser.parse(
            "def greet(name):\n    return name\n\nprint(greet('git-simplify'))\n",
            "python",
        )

        calls = CallExtractor().extract(result)

        self.assertEqual(
            [(call.function, call.arguments_count) for call in calls],
            [("print", 1), ("greet", 1)],
        )

    def test_extracts_javascript_imports(self) -> None:
        result = self.parser.parse(
            "import { readFile } from 'fs';\n",
            "javascript",
        )

        imports = ImportExtractor().extract(result)

        self.assertEqual(len(imports), 1)
        self.assertEqual(imports[0].module, "fs")
        self.assertEqual(imports[0].name, "{ readFile }")

    def test_extracts_javascript_api_routes(self) -> None:
        result = self.parser.parse(
            "app.get('/health', healthHandler);\n"
            "router.post('/users', createUser);\n",
            "javascript",
        )

        apis = ApiExtractor().extract(result)

        self.assertEqual(
            [(api.method, api.path) for api in apis],
            [("GET", "/health"), ("POST", "/users")],
        )


if __name__ == "__main__":
    unittest.main()
