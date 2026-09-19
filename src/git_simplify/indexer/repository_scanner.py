"""Traverse repositories and identify candidate source files."""

from __future__ import annotations

from collections.abc import Iterator
from os import walk
from pathlib import Path

from ..parser import SyntaxParser, UnsupportedLanguageError
from ..parser.syntax_parser import ParseResult
from .file_filter import FileFilter
from .language_detector import LanguageDetector


class RepositoryScanner:
    def __init__(
        self,
        file_filter: FileFilter | None = None,
        language_detector: LanguageDetector | None = None,
        syntax_parser: SyntaxParser | None = None,
    ) -> None:
        self.file_filter = file_filter or FileFilter()
        self.language_detector = language_detector or LanguageDetector()
        self.syntax_parser = syntax_parser or SyntaxParser()

    def scan(self, repository: str | Path) -> None:
        """Parse supported repository files, preserving the original scan API."""
        for _path, _result in self.iter_parsed_files(repository):
            pass

    def iter_parsed_files(
        self, repository: str | Path
    ) -> Iterator[tuple[Path, ParseResult]]:
        """Yield paths and parse results in deterministic traversal order.

        Unsupported grammars are skipped; file access errors propagate.
        File symlinks outside the repository are excluded.
        """
        root = Path(repository).expanduser()

        if not root.exists():
            raise FileNotFoundError(f"Repository does not exist: {root}")
        if not root.is_dir():
            raise NotADirectoryError(f"Repository is not a directory: {root}")

        for _directory, directories, files in walk(root, followlinks=False):
            directories[:] = sorted([
                directory
                for directory in directories
                if not self.file_filter.should_skip_directory(directory)
            ])

            for file_name in sorted(files):
                file_path = Path(_directory) / file_name
                if not self.file_filter.should_include_file(file_path):
                    continue

                if not file_path.resolve().is_relative_to(root.resolve()):
                    continue

                language = self.language_detector.detect(file_path)
                if language is None:
                    continue

                try:
                    result = self.syntax_parser.parse_file(file_path, language)
                except UnsupportedLanguageError:
                    # The detector knows about more languages than the grammar
                    # registry currently provides. Those files remain eligible
                    # for future parser support.
                    continue
                yield file_path, result


def scan_repository(repository: str | Path) -> None:
    RepositoryScanner().scan(repository)
