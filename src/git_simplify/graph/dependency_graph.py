"""Directed multigraph storage and iterative dependency queries."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict
import json

from .models import GraphEdge, GraphNode


class DependencyGraph:
    """Index nodes and edges by ID, preserving distinct reference occurrences.

    Re-adding identical records is idempotent. Conflicting IDs and dangling
    edges are rejected. Records are copied at the boundary so callers cannot
    mutate indexed data through metadata dictionaries.
    """

    def __init__(self) -> None:
        self._nodes: dict[str, GraphNode] = {}
        self._edges: dict[str, GraphEdge] = {}
        self._outgoing: dict[str, set[str]] = {}
        self._incoming: dict[str, set[str]] = {}

    @property
    def nodes(self) -> tuple[GraphNode, ...]:
        return tuple(deepcopy(self._nodes[key]) for key in sorted(self._nodes))

    @property
    def edges(self) -> tuple[GraphEdge, ...]:
        return tuple(deepcopy(self._edges[key]) for key in sorted(self._edges))

    def get_node(self, node_id: str) -> GraphNode:
        return deepcopy(self._nodes[node_id])

    def get_edge(self, edge_id: str) -> GraphEdge:
        return deepcopy(self._edges[edge_id])

    def add_node(self, node: GraphNode) -> None:
        self._validate(node)
        if node.id in self._nodes:
            if self._nodes[node.id] != node:
                raise ValueError(f"Conflicting node ID: {node.id}")
            return
        self._nodes[node.id] = deepcopy(node)
        self._outgoing[node.id] = set()
        self._incoming[node.id] = set()

    def add_edge(self, edge: GraphEdge) -> None:
        self._validate(edge)
        if edge.source not in self._nodes or edge.target not in self._nodes:
            raise ValueError("Both edge endpoints must exist in the graph")
        if edge.id in self._edges:
            if self._edges[edge.id] != edge:
                raise ValueError(f"Conflicting edge ID: {edge.id}")
            return
        self._edges[edge.id] = deepcopy(edge)
        self._outgoing[edge.source].add(edge.id)
        self._incoming[edge.target].add(edge.id)

    @staticmethod
    def _validate(record: GraphNode | GraphEdge) -> None:
        if not record.id or not record.kind:
            raise ValueError("Graph records require nonempty IDs and kinds")
        # Validate the promised JSON contract before modifying graph state.
        json.dumps(asdict(record), allow_nan=False)

    def outgoing(self, node_id: str, *, kind: str | None = None) -> tuple[GraphEdge, ...]:
        return self._select_edges(self._outgoing[node_id], kind)

    def incoming(self, node_id: str, *, kind: str | None = None) -> tuple[GraphEdge, ...]:
        return self._select_edges(self._incoming[node_id], kind)

    def _select_edges(self, ids: set[str], kind: str | None) -> tuple[GraphEdge, ...]:
        return tuple(
            deepcopy(self._edges[key]) for key in sorted(ids)
            if kind is None or self._edges[key].kind == kind
        )

    def dependencies_of(
        self, node_id: str, *, transitive: bool = False, kind: str = "depends_on"
    ) -> tuple[str, ...]:
        return self._traverse(node_id, transitive, kind, reverse=False)

    def dependents_of(
        self, node_id: str, *, transitive: bool = False, kind: str = "depends_on"
    ) -> tuple[str, ...]:
        return self._traverse(node_id, transitive, kind, reverse=True)

    def _traverse(self, node_id: str, transitive: bool, kind: str, reverse: bool) -> tuple[str, ...]:
        index = self._incoming if reverse else self._outgoing

        def neighbors(node: str) -> set[str]:
            return {
                edge.source if reverse else edge.target
                for key in index[node]
                if (edge := self._edges[key]).kind == kind and edge.status == "resolved"
            }

        direct = neighbors(node_id)  # Also raises KeyError for an unknown node.
        if not transitive:
            return tuple(sorted(direct))
        visited = {node_id}
        pending = list(direct)
        while pending:
            current = pending.pop()
            if current not in visited:
                visited.add(current)
                pending.extend(neighbors(current) - visited)
        return tuple(sorted(visited - {node_id}))

    def find_cycles(self, *, kind: str = "depends_on") -> tuple[tuple[str, ...], ...]:
        """Return strongly connected cycle groups, including self-loops."""
        graph = {node: self.dependencies_of(node, kind=kind) for node in self._nodes}
        reverse = {node: self.dependents_of(node, kind=kind) for node in self._nodes}
        visited: set[str] = set()
        finished = []
        for root in sorted(graph):
            pending = [(root, False)]
            while pending:
                node, exiting = pending.pop()
                if exiting:
                    finished.append(node)
                elif node not in visited:
                    visited.add(node)
                    pending.append((node, True))
                    pending.extend((other, False) for other in graph[node] if other not in visited)
        visited.clear()
        cycles = []
        for root in reversed(finished):
            if root in visited:
                continue
            component = set()
            pending_nodes = [root]
            while pending_nodes:
                node = pending_nodes.pop()
                if node not in visited:
                    visited.add(node)
                    component.add(node)
                    pending_nodes.extend(reverse[node])
            if len(component) > 1 or root in graph[root]:
                cycles.append(tuple(sorted(component)))
        return tuple(sorted(cycles))

    def to_dict(self) -> dict:
        """Return deterministic, detached JSON-compatible node and edge lists."""
        return {
            "nodes": [asdict(node) for node in self.nodes],
            "edges": [asdict(edge) for edge in self.edges],
        }
