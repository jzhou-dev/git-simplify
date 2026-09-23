"""Graph records and deterministic identifiers."""

from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha256
import json


def graph_id(kind: str, *parts: object) -> str:
    """Return an unambiguous ID independent of insertion order and checkout path."""
    payload = json.dumps(parts, ensure_ascii=True, separators=(",", ":"), sort_keys=True)
    return f"{kind}:{sha256(payload.encode()).hexdigest()}"


@dataclass(frozen=True)
class SourceLocation:
    """Zero-based coordinates; the end position is exclusive."""

    start_line: int
    start_column: int
    end_line: int
    end_column: int

    def __post_init__(self) -> None:
        if min(self.start_line, self.start_column, self.end_line, self.end_column) < 0:
            raise ValueError("Source coordinates must be nonnegative")
        if (self.end_line, self.end_column) < (self.start_line, self.start_column):
            raise ValueError("Source range ends before it starts")


@dataclass(frozen=True)
class GraphNode:
    id: str
    kind: str
    name: str
    path: str | None = None
    language: str | None = None
    location: SourceLocation | None = None
    metadata: dict = field(default_factory=dict)


@dataclass(frozen=True)
class GraphEdge:
    id: str
    source: str
    target: str
    kind: str
    location: SourceLocation | None = None
    status: str = "resolved"
    metadata: dict = field(default_factory=dict)
