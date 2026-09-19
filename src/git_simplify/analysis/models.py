"""Serializable records shared by the analysis services."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from ..extractor import ApiDefinition, CallReference, ImportReference, Symbol


@dataclass(frozen=True)
class FileAnalysis:
    """Extracted facts for a repository-relative POSIX path."""

    path: str
    language: str
    symbols: tuple[Symbol, ...] = ()
    imports: tuple[ImportReference, ...] = ()
    calls: tuple[CallReference, ...] = ()
    apis: tuple[ApiDefinition, ...] = ()
    has_syntax_errors: bool = False


@dataclass(frozen=True)
class SymbolLocation:
    path: str
    symbol: Symbol


@dataclass(frozen=True)
class ResolvedReference:
    """A reference and optional repository-local destination.

    Unresolved includes external packages, builtins and unsupported syntax;
    static analysis cannot reliably distinguish these from missing code.
    """

    source: str
    reference: ImportReference | CallReference
    status: Literal["resolved", "unresolved", "ambiguous"]
    target_path: str | None = None
    target_symbol: Symbol | None = None


@dataclass(frozen=True)
class ResolutionResult:
    imports: tuple[ResolvedReference, ...]
    calls: tuple[ResolvedReference, ...]
