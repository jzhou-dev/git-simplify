"""Tests for repository indexing components."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from git_simplify.indexer.file_filter import FileFilter
from git_simplify.indexer.language_detector import LanguageDetector
from git_simplify.indexer.repository_scanner import RepositoryScanner


class RecordingParser:
    """Parser test double that records files passed to it."""

    def __init__(self) -> None:
        self.parsed_files: list[tuple[Path, str]] = []

    def parse_file(self, file_path: str | Path, language: str) -> None:
        self.parsed_files.append((Path(file_path), language))


class LanguageDetectorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.detector = LanguageDetector()

    def test_detects_language_case_insensitively(self) -> None:
        self.assertEqual(self.detector.detect("src/main.PY"), "python")
        self.assertEqual(self.detector.detect("src/app.TSX"), "typescript")

    def test_returns_none_for_unknown_extension(self) -> None:
        self.assertIsNone(self.detector.detect("README.md"))


class FileFilterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.file_filter = FileFilter()

    def test_skips_generated_and_vendor_directories(self) -> None:
        self.assertTrue(self.file_filter.should_skip_directory(".git"))
        self.assertTrue(self.file_filter.should_skip_directory("node_modules"))
        self.assertFalse(self.file_filter.should_skip_directory("src"))

    def test_excludes_hidden_files(self) -> None:
        self.assertFalse(self.file_filter.should_include_file(".env"))
        self.assertTrue(self.file_filter.should_include_file("main.py"))


class RepositoryScannerTests(unittest.TestCase):
    def test_parses_supported_files_and_skips_filtered_files(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            (root / "src").mkdir()
            (root / "node_modules" / "package").mkdir(parents=True)
            (root / "src" / "main.py").write_text("value = 1\n", encoding="utf-8")
            (root / "src" / "app.ts").write_text("const value = 1;\n", encoding="utf-8")
            (root / "src" / ".hidden.py").write_text("value = 1\n", encoding="utf-8")
            (root / "README.md").write_text("documentation\n", encoding="utf-8")
            (root / "node_modules" / "package" / "index.py").write_text(
                "value = 1\n",
                encoding="utf-8",
            )

            parser = RecordingParser()
            scanner = RepositoryScanner(syntax_parser=parser)
            scanner.scan(root)

        parsed_files = {
            (file_path.relative_to(root).as_posix(), language)
            for file_path, language in parser.parsed_files
        }
        self.assertEqual(
            parsed_files,
            {
                ("src/main.py", "python"),
                ("src/app.ts", "typescript"),
            },
        )

    def test_rejects_missing_repository(self) -> None:
        scanner = RepositoryScanner(syntax_parser=RecordingParser())

        with self.assertRaises(FileNotFoundError):
            scanner.scan("does-not-exist")

    def test_rejects_file_as_repository(self) -> None:
        with tempfile.NamedTemporaryFile() as temporary_file:
            scanner = RepositoryScanner(syntax_parser=RecordingParser())

            with self.assertRaises(NotADirectoryError):
                scanner.scan(temporary_file.name)


if __name__ == "__main__":
    unittest.main()
