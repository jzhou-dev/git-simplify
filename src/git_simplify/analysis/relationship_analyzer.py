"""Dependency queries and circular dependency detection."""

from __future__ import annotations

from dataclasses import dataclass

from .models import FileAnalysis, ResolutionResult


@dataclass(frozen=True)
class RelationshipAnalysis:
    """Sorted file adjacency lists and strongly connected cycle groups."""

    dependencies: dict[str, tuple[str, ...]]
    dependents: dict[str, tuple[str, ...]]
    cycles: tuple[tuple[str, ...], ...]

    def dependencies_of(self, path: str, *, transitive: bool = False) -> tuple[str, ...]:
        return self._query(self.dependencies, path, transitive)

    def dependents_of(self, path: str, *, transitive: bool = False) -> tuple[str, ...]:
        return self._query(self.dependents, path, transitive)

    @staticmethod
    def _query(graph: dict[str, tuple[str, ...]], path: str, transitive: bool) -> tuple[str, ...]:
        if not transitive:
            return graph[path]
        pending = list(graph[path])
        visited = {path}
        while pending:
            node = pending.pop()
            if node not in visited:
                visited.add(node)
                pending.extend(graph[node])
        return tuple(sorted(visited - {path}))


class RelationshipAnalyzer:
    def analyze(
        self, files: tuple[FileAnalysis, ...], resolution: ResolutionResult
    ) -> RelationshipAnalysis:
        """Build import/re-export dependencies; calls remain separate references."""
        outgoing: dict[str, set[str]] = {file.path: set() for file in files}
        incoming: dict[str, set[str]] = {file.path: set() for file in files}
        for ref in resolution.imports:
            if ref.status == "resolved" and ref.target_path is not None:
                outgoing[ref.source].add(ref.target_path)
                incoming[ref.target_path].add(ref.source)
        dependencies = {p: tuple(sorted(v)) for p, v in sorted(outgoing.items())}
        dependents = {p: tuple(sorted(v)) for p, v in sorted(incoming.items())}
        return RelationshipAnalysis(dependencies, dependents, self._cycles(dependencies, dependents))

    @staticmethod
    def _cycles(
        graph: dict[str, tuple[str, ...]], reverse: dict[str, tuple[str, ...]]
    ) -> tuple[tuple[str, ...], ...]:
        # Iterative Kosaraju traversal avoids recursion limits on large repositories.
        visited: set[str] = set()
        finished: list[str] = []
        for root in graph:
            stack = [(root, False)]
            while stack:
                node, exiting = stack.pop()
                if exiting:
                    finished.append(node)
                elif node not in visited:
                    visited.add(node)
                    stack.append((node, True))
                    stack.extend((neighbor, False) for neighbor in reversed(graph[node]) if neighbor not in visited)
        visited.clear()
        cycles = []
        for root in reversed(finished):
            if root in visited:
                continue
            component = set()
            pending = [root]
            while pending:
                node = pending.pop()
                if node not in visited:
                    visited.add(node)
                    component.add(node)
                    pending.extend(reverse[node])
            if len(component) > 1 or root in graph[root]:
                cycles.append(tuple(sorted(component)))
        return tuple(sorted(cycles))
