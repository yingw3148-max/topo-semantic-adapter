"""Tests for the internal model -> toposphere_core bridge."""

from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("toposphere_core")

from toposphere_core import Edge as TopoEdge, Node as TopoNode
from toposphere_core.types import EdgeKind, NodeKind

from topo_semantic_adapter.models import Edge, Node
from topo_semantic_adapter.toposphere_bridge import convert_edge, convert_node


def test_convert_device_node():
    node = Node(
        id="core-sw-01:device:core-sw-01",
        kind="device",
        label="core-sw-01",
        properties={"name": "core-sw-01"},
        source="display lldp neighbor",
    )
    topo = convert_node(node, source_file=Path("/tmp/file"), producer="LldpNeighborParser")

    assert isinstance(topo, TopoNode)
    assert topo.id == "core-sw-01:device:core-sw-01"
    assert topo.name == "core-sw-01"
    assert topo.kind == NodeKind.DEVICE
    assert topo.metadata["name"] == "core-sw-01"
    assert len(topo.provenance) == 1
    assert topo.provenance[0].producer == "LldpNeighborParser"
    assert topo.provenance[0].locator == "display lldp neighbor"


def test_convert_interface_node():
    node = Node(
        id="core-sw-01:interface:GigabitEthernet0/0/1",
        kind="interface",
        properties={"name": "GigabitEthernet0/0/1"},
    )
    topo = convert_node(node)
    assert topo.kind == NodeKind.INTERFACE
    assert topo.metadata["name"] == "GigabitEthernet0/0/1"


def test_convert_unknown_kind_is_preserved():
    node = Node(id="a:custom:1", kind="custom_kind")
    topo = convert_node(node)
    assert topo.kind == "custom_kind"


def test_convert_connects_to_edge():
    edge = Edge(
        id="a--connects-to--b",
        source="a",
        target="b",
        relation="connects_to",
        properties={"protocol": "lldp"},
        provenance="display lldp neighbor",
    )
    topo = convert_edge(edge, producer="LldpNeighborParser")

    assert isinstance(topo, TopoEdge)
    assert topo.source == "a"
    assert topo.target == "b"
    assert topo.kind == EdgeKind.CONNECTS_TO
    assert topo.metadata["protocol"] == "lldp"
    assert topo.id == "a--connects-to--b"
    assert topo.provenance[0].producer == "LldpNeighborParser"
    assert topo.provenance[0].locator == "display lldp neighbor"


def test_convert_member_of_edge():
    edge = Edge(
        id="port--member-of--lag",
        source="port",
        target="lag",
        relation="member_of",
        properties={"selected_status": "Selected"},
    )
    topo = convert_edge(edge)
    assert topo.kind == EdgeKind.MEMBER_OF
    assert topo.metadata["selected_status"] == "Selected"
