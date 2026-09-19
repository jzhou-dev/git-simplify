"""Traverse repositories and identify candidate source files."""

from __future__ import annotations

from os import walk
from pathlib import Path

from ..parser import SyntaxParser, UnsupportedLanguageError
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
        """Traverse every directory and file beneath ``repository``.

        Ignored directories are pruned from traversal, and unsupported or
        hidden files are skipped. Supported source files are parsed, but parse
        results are intentionally discarded until extraction is implemented.
        """
        root = Path(repository).expanduser()

        if not root.exists():
            raise FileNotFoundError(f"Repository does not exist: {root}")
        if not root.is_dir():
            raise NotADirectoryError(f"Repository is not a directory: {root}")

        for _directory, directories, files in walk(root, followlinks=False):
            directories[:] = [
                directory
                for directory in directories
                if not self.file_filter.should_skip_directory(directory)
            ]

            for file_name in files:
                file_path = Path(_directory) / file_name
                if not self.file_filter.should_include_file(file_path):
                    continue

                language = self.language_detector.detect(file_path)
                if language is None:
                    continue

                try:
                    self.syntax_parser.parse_file(file_path, language)
                except UnsupportedLanguageError:
                    # The detector knows about more languages than the grammar
                    # registry currently provides. Those files remain eligible
                    # for future parser support.
                    continue


def scan_repository(repository: str | Path) -> None:
    RepositoryScanner().scan(repository)
