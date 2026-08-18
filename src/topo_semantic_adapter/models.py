"""Portable graph model used as the canonical output of the adapter layer.

This module intentionally does not depend on ``topograph-py``; the integration
boundary is a thin translator that converts ``Graph``/``Node``/``Edge`` into the
storage backend used by the sibling project.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Node:
    """A topology entity (device, interface, aggregation group, etc.)."""

    id: str
    kind: str
    label: str | None = None
    properties: dict[str, Any] = field(default_factory=dict)
    source: str | None = None  # command/adapter that produced the node

    def __post_init__(self) -> None:
        if self.label is None:
            self.label = self.id


@dataclass
class Edge:
    """A relationship between two topology entities."""

    id: str
    source: str
    target: str
    relation: str
    properties: dict[str, Any] = field(default_factory=dict)
    provenance: str | None = None  # command/adapter that produced the edge
    confidence: str = "EXTRACTED"  # EXTRACTED | INFERRED | AMBIGUOUS


@dataclass
class Graph:
    """A simple in-memory property graph."""

    nodes: dict[str, Node] = field(default_factory=dict)
    edges: dict[str, Edge] = field(default_factory=dict)

    def add_node(self, node: Node) -> Node:
        """Add a node, merging properties if it already exists."""
        existing = self.nodes.get(node.id)
        if existing is not None:
            existing.properties.update(node.properties)
            if node.label:
                existing.label = node.label
            return existing
        self.nodes[node.id] = node
        return node

    def add_edge(self, edge: Edge) -> Edge:
        """Add an edge, merging properties if it already exists."""
        existing = self.edges.get(edge.id)
        if existing is not None:
            existing.properties.update(edge.properties)
            return existing
        self.edges[edge.id] = edge
        return edge

    def merge(self, other: Graph) -> Graph:
        """Merge another graph into this one."""
        for node in other.nodes.values():
            self.add_node(node)
        for edge in other.edges.values():
            self.add_edge(edge)
        return self
