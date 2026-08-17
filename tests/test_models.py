"""Tests for the internal property graph model."""

from __future__ import annotations

from topo_semantic_adapter.models import Edge, Graph, Node


def test_graph_add_node():
    graph = Graph()
    node = Node(id="a", kind="device", label="A")
    assert graph.add_node(node) is node
    assert graph.nodes["a"] is node


def test_graph_merge_node_properties():
    graph = Graph()
    graph.add_node(Node(id="a", kind="interface", properties={"name": "GE0/0/1"}))
    merged = graph.add_node(
        Node(id="a", kind="interface", properties={"state": "up"})
    )
    assert merged.properties == {"name": "GE0/0/1", "state": "up"}


def test_graph_merge_updates_label():
    graph = Graph()
    graph.add_node(Node(id="a", kind="device", label="old"))
    merged = graph.add_node(Node(id="a", kind="device", label="new"))
    assert merged.label == "new"


def test_graph_merge_edges():
    graph = Graph()
    graph.add_edge(Edge(id="e1", source="a", target="b", relation="connects_to"))
    merged = graph.add_edge(
        Edge(
            id="e1",
            source="a",
            target="b",
            relation="connects_to",
            properties={"protocol": "lldp"},
        )
    )
    assert merged.properties == {"protocol": "lldp"}


def test_graph_merge_other_graph():
    g1 = Graph()
    g1.add_node(Node(id="a", kind="device"))
    g1.add_edge(Edge(id="e1", source="a", target="b", relation="connects_to"))

    g2 = Graph()
    g2.add_node(Node(id="b", kind="device"))
    g2.add_node(Node(id="a", kind="device", properties={"role": "core"}))
    g2.add_edge(Edge(id="e2", source="b", target="c", relation="connects_to"))

    result = g1.merge(g2)
    assert result is g1
    assert set(g1.nodes) == {"a", "b"}
    assert g1.nodes["a"].properties["role"] == "core"
    assert "e1" in g1.edges
    assert "e2" in g1.edges
