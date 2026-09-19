"""Tree-sitter grammar registry and language loading."""

from __future__ import annotations

from importlib import import_module
from typing import Any

from tree_sitter import Language


class UnsupportedLanguageError(ValueError):
    """Raised when git-simplify has no configured grammar for a language."""


# The values identify the grammar package and its language factory. TypeScript
# publishes separate factories for TypeScript and TSX grammars.
GRAMMAR_SPECS: dict[str, tuple[str, str]] = {
    "javascript": ("tree_sitter_javascript", "language"),
    "python": ("tree_sitter_python", "language"),
    "typescript": ("tree_sitter_typescript", "language_typescript"),
    "tsx": ("tree_sitter_typescript", "language_tsx"),
}


def supported_languages() -> tuple[str, ...]:
    """Return the language names known by the grammar registry."""
    return tuple(GRAMMAR_SPECS)


def load_language(language_name: str) -> Language:
    """Load and return the Tree-sitter grammar for ``language_name``."""
    normalized_name = language_name.lower()
    try:
        package_name, factory_name = GRAMMAR_SPECS[normalized_name]
    except KeyError as error:
        supported = ", ".join(supported_languages())
        raise UnsupportedLanguageError(
            f"Unsupported language '{language_name}'. Supported languages: {supported}"
        ) from error

    try:
        grammar_package = import_module(package_name)
        factory: Any = getattr(grammar_package, factory_name)
    except (ImportError, AttributeError) as error:
        raise UnsupportedLanguageError(
            f"Tree-sitter grammar package is unavailable for '{normalized_name}'"
        ) from error

    return Language(factory())
