"""Orchestrate scanning, extraction, resolution and relationship analysis."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path

from ..extractor import ApiExtractor, CallExtractor, ImportExtractor, SymbolExtractor
from ..indexer import RepositoryScanner
from .models import FileAnalysis, ResolutionResult
from .relationship_analyzer import RelationshipAnalysis, RelationshipAnalyzer
from .symbol_resolver import SymbolResolver


@dataclass(frozen=True)
class ProjectAnalysis:
    root: str
    files: tuple[FileAnalysis, ...]
    resolution: ResolutionResult
    relationships: RelationshipAnalysis

    def to_dict(self) -> dict:
        """Return plain records suitable for json.dumps, with no syntax trees."""
        return asdict(self)


class ProjectAnalyzer:
    def __init__(
        self,
        scanner: RepositoryScanner | None = None,
        *,
        source_roots: tuple[str, ...] = ("", "src"),
    ) -> None:
        self.scanner = scanner or RepositoryScanner()
        self.source_roots = source_roots

    def analyze(self, repository: str | Path) -> ProjectAnalysis:
        """Analyze supported files without executing repository code.

        Syntax errors are recorded and partial extraction continues. I/O errors
        propagate to the caller. Each invocation produces a fresh snapshot.
        """
        root = Path(repository).expanduser().resolve()
        files = []
        for path, parsed in self.scanner.iter_parsed_files(root):
            apis = ApiExtractor().extract(parsed)
            # Decorators and their nested call nodes can describe the same route.
            unique_apis = {(a.method, a.path, a.start_line): a for a in apis}
            files.append(FileAnalysis(
                path=path.relative_to(root).as_posix(),
                language=parsed.language,
                symbols=tuple(SymbolExtractor().extract(parsed)),
                imports=tuple(ImportExtractor().extract(parsed)),
                calls=tuple(CallExtractor().extract(parsed)),
                apis=tuple(unique_apis.values()),
                has_syntax_errors=parsed.has_errors,
            ))
        ordered = tuple(sorted(files, key=lambda file: file.path))
        resolution = SymbolResolver(ordered, self.source_roots).resolve()
        relationships = RelationshipAnalyzer().analyze(ordered, resolution)
        return ProjectAnalysis(str(root), ordered, resolution, relationships)


def analyze_project(repository: str | Path) -> ProjectAnalysis:
    """Analyze a repository with the default scanner and source roots."""
    return ProjectAnalyzer().analyze(repository)
