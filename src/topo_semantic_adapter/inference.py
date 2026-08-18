"""Inferred topology reconstruction.

This module performs a second pass over an already-built graph and adds nodes
and edges that are not explicitly present in the CLI output but can be
reasonably deduced from it. All inferred facts are marked with
``confidence="INFERRED"`` so consumers can distinguish them from extracted
facts.

Current inference rules:

1. **OSPF peer topology** - For every interface that reports an OSPF neighbor,
   create an ``ospf_router`` node and a ``peers_with`` edge to the local device.
2. **LLDP reverse edges** - If device A reports a link to device B but B does
   not report a link back, create the reverse ``connects_to`` edge so the
   topology is closed under both directions.
"""

from __future__ import annotations

from toposphere_core.types import GraphView, kind_value

from topo_semantic_adapter.models import Edge, Graph, Node


def _device_node_id(source: str) -> str:
    return f"{source}:device:{source}"


def infer_ospf_topology(view: GraphView) -> Graph:
    """Infer OSPF router nodes and ``peers_with`` edges from interface metadata.

    Every interface node that carries ``ospf_neighbor_router_id`` implies an
    OSPF adjacency. We materialize the remote router as an ``ospf_router`` node
    and link the local device to it with a ``peers_with`` edge.
    """
    graph = Graph()
    seen_routers: set[str] = set()

    for node in view.nodes.values():
        if kind_value(node.kind) != "interface":
            continue

        router_id = node.metadata.get("ospf_neighbor_router_id")
        state = node.metadata.get("ospf_neighbor_state")
        if not router_id:
            continue

        # Derive the local device source from the interface node id:
        #   {source}:interface:{name}
        parts = node.id.split(":interface:", 1)
        if len(parts) != 2:
            continue
        local_source = parts[0]
        local_device_id = _device_node_id(local_source)

        router_node_id = f"inferred:ospf_router:{router_id}"
        if router_node_id not in seen_routers:
            graph.add_node(
                Node(
                    id=router_node_id,
                    kind="ospf_router",
                    label=router_id,
                    properties={
                        "router_id": router_id,
                        "inferred": True,
                    },
                    source="inferred_ospf_topology",
                    confidence="INFERRED",
                )
            )
            seen_routers.add(router_node_id)

        edge_id = f"{local_device_id}--peers-with--{router_node_id}"
        graph.add_edge(
            Edge(
                id=edge_id,
                source=local_device_id,
                target=router_node_id,
                relation="peers_with",
                properties={
                    "protocol": "ospf",
                    "ospf_state": state,
                    "inferred": True,
                },
                provenance="inferred_ospf_topology",
                confidence="INFERRED",
            )
        )

    return graph


def infer_lldp_reverse_edges(view: GraphView) -> Graph:
    """Create reverse ``connects_to`` edges for one-sided LLDP observations.

    LLDP is inherently directional in the data (each device reports its own
    perspective). If A->B exists but B->A does not, we infer the reverse edge
    so downstream algorithms see a closed bidirectional link.
    """
    graph = Graph()
    observed_pairs: set[tuple[str, str]] = {
        (edge.source, edge.target)
        for edge in view.edges
        if kind_value(edge.kind) == "connects_to"
    }

    for edge in view.edges:
        if kind_value(edge.kind) != "connects_to":
            continue
        reverse_pair = (edge.target, edge.source)
        if reverse_pair in observed_pairs:
            continue

        reverse_id = f"{edge.target}--connects-to--{edge.source}"
        graph.add_edge(
            Edge(
                id=reverse_id,
                source=edge.target,
                target=edge.source,
                relation="connects_to",
                properties={
                    "protocol": edge.metadata.get("protocol", "lldp"),
                    "inferred": True,
                },
                provenance="inferred_lldp_reverse",
                confidence="INFERRED",
            )
        )

    return graph


def infer_topology(view: GraphView) -> Graph:
    """Run all inference rules and return the inferred subgraph."""
    graph = Graph()
    graph.merge(infer_ospf_topology(view))
    graph.merge(infer_lldp_reverse_edges(view))
    return graph
