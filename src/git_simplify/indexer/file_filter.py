"""Rules for excluding repository files and directories from indexing."""

from __future__ import annotations

from pathlib import Path


DEFAULT_IGNORED_DIRECTORIES = {
    ".git",
    ".hg",
    ".svn",
    ".venv",
    "__pycache__",
    "build",
    "dist",
    "node_modules",
    "venv",
}


class FileFilter:
    """Determine whether a repository path is eligible for indexing."""

    def __init__(
        self,
        ignored_directories: set[str] | None = None,
    ) -> None:
        self.ignored_directories = (
            ignored_directories
            if ignored_directories is not None
            else DEFAULT_IGNORED_DIRECTORIES
        )

    def should_skip_directory(self, directory_name: str) -> bool:
        """Return whether a directory should be excluded from traversal."""
        return directory_name in self.ignored_directories

    def should_include_file(self, file_path: str | Path) -> bool:
        """Return whether a file is eligible for language detection."""
        return not Path(file_path).name.startswith(".")
