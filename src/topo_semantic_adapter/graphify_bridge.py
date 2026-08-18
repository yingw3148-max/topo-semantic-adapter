"""Bridge from ``toposphere_core.TopoGraph`` to graphify's nodes/edges schema.

The adapter layer already performs deterministic extraction (LLDP, OSPF, LAG,
VRRP, DHCP). This module exports those results into the graphify pipeline so
that downstream clustering, analysis, and reporting can be reused.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from toposphere_core import TopoGraph


def to_graphify_extractions(
    topo_graph: TopoGraph,
    *,
    root: Path | None = None,
) -> dict[str, Any]:
    """Convert a populated ``TopoGraph`` into graphify's extraction dict.

    The returned dict follows graphify's ``{nodes, edges}`` schema and can be
    passed directly to ``graphify.build.build()``.
    """
    root = root or Path(".").resolve()

    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []

    for node in topo_graph.get_all_nodes():
        nodes.append(_convert_node(node, root))

    for edge in topo_graph.get_all_edges():
        edges.append(_convert_edge(edge))

    return {"nodes": nodes, "edges": edges}


def _convert_node(node: Any, root: Path) -> dict[str, Any]:
    """Convert a ``toposphere_core.Node`` to a graphify node dict."""
    metadata = dict(node.metadata or {})
    provenance = _first_provenance(node.provenance)

    source_file = provenance.get("artifact_ref") if provenance else None
    if source_file:
        source_file = _make_relative(source_file, root)

    # graphify expects string kinds and labels.
    kind = str(node.kind.value if hasattr(node.kind, "value") else node.kind)
    label = node.name or node.id

    # graphify's schema requires file_type on every node. Topology entities are
    # conceptual nodes extracted from operational data rather than source files.
    file_type = "concept"

    result: dict[str, Any] = {
        "id": node.id,
        "label": label,
        "kind": kind,
        "file_type": file_type,
        "source_file": source_file,
        "metadata": metadata,
    }
    if provenance:
        result["metadata"]["provenance"] = provenance
    return result


def _convert_edge(edge: Any) -> dict[str, Any]:
    """Convert a ``toposphere_core.Edge`` to a graphify edge dict."""
    metadata = dict(edge.metadata or {})
    provenance = _first_provenance(edge.provenance)

    relation = (
        edge.relation_key
        if getattr(edge, "relation_key", None)
        else str(edge.kind.value if hasattr(edge.kind, "value") else edge.kind)
    )

    confidence = metadata.get("confidence", "EXTRACTED")
    source_file = provenance.get("artifact_ref") if provenance else None

    # graphify's schema requires source_file on every edge.
    result: dict[str, Any] = {
        "source": edge.source,
        "target": edge.target,
        "relation": relation,
        "source_file": source_file or "",
        "confidence": confidence,
        "metadata": metadata,
    }
    if provenance:
        result["metadata"]["provenance"] = provenance
    return result


def _first_provenance(provenance_tuple: tuple) -> dict[str, Any] | None:
    """Return the first provenance entry as a plain dict, if any."""
    if not provenance_tuple:
        return None
    prov = provenance_tuple[0]
    return {
        "artifact_ref": prov.artifact_ref,
        "locator": prov.locator,
        "method": prov.method,
        "producer": prov.producer,
        "producer_version": prov.producer_version,
        "observed_at": prov.observed_at,
        "confidence": prov.confidence,
    }


def _make_relative(path: str, root: Path) -> str:
    """Return a path string relative to ``root`` when possible."""
    try:
        return str(Path(path).resolve().relative_to(root.resolve()))
    except ValueError:
        return path
