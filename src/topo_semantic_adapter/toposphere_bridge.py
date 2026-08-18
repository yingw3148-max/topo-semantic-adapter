"""Bridge from the adapter's internal model to ``toposphere_core`` types.

The output target of this package is ``toposphere_core.TopoGraph``. This module
converts the lightweight intermediate ``Node``/``Edge`` produced by parsers into
the canonical ``toposphere_core.Node`` and ``toposphere_core.Edge`` that the
persistent graph store expects.
"""

from __future__ import annotations

from pathlib import Path

from toposphere_core import Edge as TopoEdge, Node as TopoNode, Provenance
from toposphere_core.types import parse_edge_kind, parse_node_kind

from topo_semantic_adapter.models import Edge, Node


def _to_node_kind(value: str):
    try:
        return parse_node_kind(value)
    except (ValueError, TypeError):
        return value


def _to_edge_kind(value: str):
    try:
        return parse_edge_kind(value)
    except (ValueError, TypeError):
        return value


def _make_provenance(
    source_file: Path | None,
    locator: str | None,
    producer: str | None,
) -> tuple[Provenance, ...]:
    if source_file is None and locator is None and producer is None:
        return ()
    return (
        Provenance(
            artifact_ref=str(source_file) if source_file else None,
            locator=locator,
            producer=producer,
            method="cli_parsing",
        ),
    )


def convert_node(
    node: Node,
    *,
    source_file: Path | None = None,
    producer: str | None = None,
) -> TopoNode:
    """Convert an adapter internal node into a ``toposphere_core.Node``."""
    return TopoNode(
        id=node.id,
        name=node.label or node.id,
        kind=_to_node_kind(node.kind),
        metadata=dict(node.properties),
        provenance=_make_provenance(source_file, node.source, producer),
    )


def convert_edge(
    edge: Edge,
    *,
    source_file: Path | None = None,
    producer: str | None = None,
) -> TopoEdge:
    """Convert an adapter internal edge into a ``toposphere_core.Edge``."""
    metadata = dict(edge.properties)
    metadata.setdefault("confidence", edge.confidence)
    return TopoEdge(
        source=edge.source,
        target=edge.target,
        kind=_to_edge_kind(edge.relation),
        metadata=metadata,
        id=edge.id,
        provenance=_make_provenance(source_file, edge.provenance or edge.relation, producer),
    )
