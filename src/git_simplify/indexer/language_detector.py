"""Detect source languages from file extensions."""

from __future__ import annotations

from pathlib import Path


LANGUAGE_EXTENSIONS: dict[str, str] = {
    ".c": "c",
    ".cc": "cpp",
    ".cpp": "cpp",
    ".cs": "csharp",
    ".go": "go",
    ".h": "c",
    ".hh": "cpp",
    ".hpp": "cpp",
    ".java": "java",
    ".js": "javascript",
    ".jsx": "javascript",
    ".kt": "kotlin",
    ".php": "php",
    ".py": "python",
    ".rb": "ruby",
    ".rs": "rust",
    ".scala": "scala",
    ".sh": "shell",
    ".swift": "swift",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".vue": "vue",
}


class LanguageDetector:
    """Map supported source-file extensions to language names."""

    def __init__(self, extensions: dict[str, str] | None = None) -> None:
        self.extensions = extensions or LANGUAGE_EXTENSIONS

    def detect(self, file_path: str | Path) -> str | None:
        """Return the detected language, or ``None`` if unsupported."""
        return self.extensions.get(Path(file_path).suffix.lower())
