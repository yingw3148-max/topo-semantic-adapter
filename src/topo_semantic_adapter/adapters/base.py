"""Core abstractions for semantic adapters and command-level parsers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Iterable

from topo_semantic_adapter.models import Edge, Graph, Node


@dataclass(frozen=True)
class AdapterContext:
    """Runtime context passed to every parser."""

    device_ip: str
    device_id: str
    site: str
    intent: str | None = None
    extras: dict[str, Any] = field(default_factory=dict)


@dataclass
class ParsedEntity:
    """A collection of nodes and edges produced by a single parser invocation."""

    nodes: list[Node] = field(default_factory=list)
    edges: list[Edge] = field(default_factory=list)

    def to_graph(self) -> Graph:
        graph = Graph()
        for node in self.nodes:
            graph.add_node(node)
        for edge in self.edges:
            graph.add_edge(edge)
        return graph


class CommandParser(ABC):
    """A command-level parser that knows how to extract topology entities.

    Implementations declare which commands they understand via ``can_parse``
    and return ``ParsedEntity`` from ``parse``.
    """

    @property
    def semantic_concepts(self) -> tuple[str, ...]:
        """Concepts/attributes this parser contributes (used by intent filtering)."""
        return ()

    @abstractmethod
    def can_parse(self, command: str) -> bool:
        """Return True if this parser can handle ``command``."""
        ...

    @abstractmethod
    def parse(self, command: str, output: str, context: AdapterContext) -> ParsedEntity:
        """Parse ``output`` and return extracted entities."""
        ...


class SemanticAdapter(ABC):
    """A vendor/technology-level adapter that groups related ``CommandParser``s."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable adapter name."""
        ...

    @property
    @abstractmethod
    def vendor(self) -> str:
        """Vendor or data-source identifier (e.g. ``huawei``)."""
        ...

    @abstractmethod
    def supported_parsers(self) -> Iterable[CommandParser]:
        """Return the parsers provided by this adapter."""
        ...
