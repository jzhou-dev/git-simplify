"""Construct graphs from existing analysis snapshots, without reparsing files."""

from __future__ import annotations

from dataclasses import asdict
from pathlib import PurePosixPath

from ..analysis import ProjectAnalysis
from ..extractor import ApiDefinition, CallReference, ImportReference, Symbol
from .dependency_graph import DependencyGraph
from .models import GraphEdge, GraphNode, SourceLocation, graph_id


def _location(record: Symbol | ApiDefinition | ImportReference | CallReference) -> SourceLocation:
    return SourceLocation(record.start_line, record.start_column, record.end_line, record.end_column)


def _symbol_id(path: str, symbol: Symbol) -> str:
    return graph_id("symbol", path, asdict(symbol))


class GraphBuilder:
    """Build containment, declaration, import, call and dependency edges.

    Calls originate at files: current analysis does not identify lexical callers.
    Unresolved/ambiguous references have explicit reference nodes; they are not
    assumed to be external packages or included in dependency traversal.
    """

    def build(self, analysis: ProjectAnalysis) -> DependencyGraph:
        graph = DependencyGraph()
        graph.add_node(GraphNode("repository", "repository", PurePosixPath(analysis.root).name or "/", metadata={"root": analysis.root}))
        paths = set()
        for file in sorted(analysis.files, key=lambda item: item.path):
            path = PurePosixPath(file.path)
            if path.is_absolute() or ".." in path.parts or str(path) != file.path or not path.name:
                raise ValueError(f"Expected a canonical repository-relative path: {file.path}")
            if file.path in paths:
                raise ValueError(f"Duplicate file path: {file.path}")
            paths.add(file.path)
            parent_id = "repository"
            for directory in reversed(path.parents):
                if str(directory) == ".":
                    continue
                directory_id = graph_id("directory", str(directory))
                graph.add_node(GraphNode(directory_id, "directory", directory.name, str(directory)))
                self._edge(graph, parent_id, directory_id, "contains")
                parent_id = directory_id
            file_id = graph_id("file", file.path)
            graph.add_node(GraphNode(file_id, "file", path.name, file.path, file.language, metadata={"has_syntax_errors": file.has_syntax_errors}))
            self._edge(graph, parent_id, file_id, "contains")
            for symbol in file.symbols:
                symbol_id = _symbol_id(file.path, symbol)
                graph.add_node(GraphNode(symbol_id, symbol.kind, symbol.name, file.path, file.language, _location(symbol)))
                self._edge(graph, file_id, symbol_id, "defines")
            for api in file.apis:
                api_id = graph_id("api", file.path, asdict(api))
                graph.add_node(GraphNode(api_id, "api", api.name, file.path, file.language, _location(api), {"method": api.method, "route": api.path}))
                self._edge(graph, file_id, api_id, "defines")

        for resolved in (*analysis.resolution.imports, *analysis.resolution.calls):
            ref = resolved.reference
            source_id = graph_id("file", resolved.source)
            is_import = isinstance(ref, ImportReference)
            kind = ("exports" if ref.kind == "export" else "imports") if is_import else "calls"
            location = _location(ref)
            if resolved.status == "resolved":
                if resolved.target_path is None:
                    raise ValueError("Resolved references require a target path")
                target_id = (
                    _symbol_id(resolved.target_path, resolved.target_symbol)
                    if resolved.target_symbol is not None
                    else graph_id("file", resolved.target_path)
                )
            elif resolved.status in {"unresolved", "ambiguous"}:
                target_id = graph_id("reference", resolved.source, kind, asdict(ref), resolved.status)
                name = ref.module if is_import else ref.function
                graph.add_node(GraphNode(target_id, "reference", name, resolved.source, location=location, metadata={"status": resolved.status, "reference": asdict(ref)}))
            else:
                raise ValueError(f"Unknown resolution status: {resolved.status}")
            self._edge(graph, source_id, target_id, kind, location, resolved.status, asdict(ref))
            if is_import and resolved.status == "resolved":
                self._edge(graph, source_id, graph_id("file", resolved.target_path), "depends_on")
        return graph

    @staticmethod
    def _edge(
        graph: DependencyGraph, source: str, target: str, kind: str,
        location: SourceLocation | None = None, status: str = "resolved",
        metadata: dict | None = None,
    ) -> None:
        metadata = {} if metadata is None else metadata
        edge_id = graph_id("edge", source, target, kind, asdict(location) if location else None, status, metadata)
        graph.add_edge(GraphEdge(edge_id, source, target, kind, location, status, metadata))


def build_graph(analysis: ProjectAnalysis) -> DependencyGraph:
    return GraphBuilder().build(analysis)
