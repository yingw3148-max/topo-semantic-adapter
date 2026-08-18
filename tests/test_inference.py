"""Tests for inferred topology reconstruction."""

from __future__ import annotations

from topo_semantic_adapter import CLIFileLoader, GraphBuilder
from topo_semantic_adapter.adapters.base import AdapterContext
from topo_semantic_adapter.adapters.huawei.ospf import OspfNeighborParser
from topo_semantic_adapter.inference import (
    infer_lldp_reverse_edges,
    infer_ospf_topology,
    infer_topology,
)
from topo_semantic_adapter.registry import AdapterRegistry


def _build_view(site_path, *, infer: bool = False):
    loader = CLIFileLoader(site_name="湖北大学配置", base_path=site_path.parent)
    blocks = list(loader.iter_blocks())

    registry = AdapterRegistry()
    registry.load_builtin()
    builder = GraphBuilder(registry=registry, db_path=":memory:", infer=infer)
    builder.consume_many(blocks)
    graph = builder.build()
    return graph.to_graphview(), graph


def test_infer_ospf_topology_creates_router_node():
    parser = OspfNeighborParser()
    context = AdapterContext(
        device_ip="10.0.0.1", device_id="core-sw-01", site="site-a"
    )
    output = """OSPF Process 1 with Router ID 1.1.1.1
 Area 0.0.0.0 interface 10.1.1.1(GigabitEthernet0/0/1)'s neighbors
 Router ID: 2.2.2.2          Address: 10.1.1.2
   State: Full           Mode:Nbr is Master           Priority: 1
"""
    entities = parser.parse("display ospf peer", output, context)
    graph = entities.to_graph()
    view = graph.to_graphview() if hasattr(graph, "to_graphview") else None

    # The internal Graph model does not have to_graphview; test the inference
    # directly on a small GraphView built from the parsed entities via the
    # bridge.
    from topo_semantic_adapter.toposphere_bridge import convert_edge, convert_node
    from toposphere_core import TopoGraph

    topo = TopoGraph(":memory:")
    for node in entities.nodes:
        topo.add_node(convert_node(node))
    for edge in entities.edges:
        topo.add_edge(convert_edge(edge))
    view = topo.to_graphview()

    inferred = infer_ospf_topology(view)
    router_ids = {
        node.id for node in inferred.nodes.values() if node.kind == "ospf_router"
    }
    assert "inferred:ospf_router:2.2.2.2" in router_ids

    peer_edges = [
        edge for edge in inferred.edges.values() if edge.relation == "peers_with"
    ]
    assert len(peer_edges) == 1
    assert peer_edges[0].source == "core-sw-01:device:core-sw-01"
    assert peer_edges[0].target == "inferred:ospf_router:2.2.2.2"
    assert peer_edges[0].confidence == "INFERRED"


def test_infer_lldp_reverse_edge_for_one_sided_lldp():
    from toposphere_core import TopoGraph

    from topo_semantic_adapter.models import Edge, Graph, Node
    from topo_semantic_adapter.toposphere_bridge import convert_edge, convert_node

    graph = Graph()
    graph.add_node(Node(id="a:interface:GE0/0/1", kind="interface"))
    graph.add_node(Node(id="b:interface:GE0/0/2", kind="interface"))
    graph.add_edge(
        Edge(
            id="a--connects-to--b",
            source="a:interface:GE0/0/1",
            target="b:interface:GE0/0/2",
            relation="connects_to",
            properties={"protocol": "lldp"},
        )
    )

    topo = TopoGraph(":memory:")
    for node in graph.nodes.values():
        topo.add_node(convert_node(node))
    for edge in graph.edges.values():
        topo.add_edge(convert_edge(edge))
    view = topo.to_graphview()

    inferred = infer_lldp_reverse_edges(view)
    assert len(inferred.edges) == 1
    edge = inferred.edges["b:interface:GE0/0/2--connects-to--a:interface:GE0/0/1"]
    assert edge.source == "b:interface:GE0/0/2"
    assert edge.target == "a:interface:GE0/0/1"
    assert edge.confidence == "INFERRED"


def test_graph_builder_with_infer_adds_ospf_router(fixture_site_path):
    view, graph = _build_view(fixture_site_path, infer=True)

    router_ids = {
        node_id
        for node_id, node in view.nodes.items()
        if node.kind == "ospf_router"
    }
    assert "inferred:ospf_router:2.2.2.2" in router_ids

    peer_edges = [
        edge for edge in view.edges if edge.kind == "peers_with"
    ]
    assert len(peer_edges) == 1
    assert peer_edges[0].metadata.get("confidence") == "INFERRED"
    graph.close()


def test_graph_builder_without_infer_keeps_original_counts(fixture_site_path):
    view, graph = _build_view(fixture_site_path, infer=False)

    router_ids = {
        node_id
        for node_id, node in view.nodes.items()
        if node.kind == "ospf_router"
    }
    assert router_ids == set()
    graph.close()


def test_infer_topology_combines_rules(fixture_site_path):
    view, graph = _build_view(fixture_site_path, infer=True)
    # OSPF router node + peers_with edge; LLDP is already symmetric so no
    # reverse edges are inferred.
    assert any(node.kind == "ospf_router" for node in view.nodes.values())
    assert any(edge.kind == "peers_with" for edge in view.edges)
    graph.close()
