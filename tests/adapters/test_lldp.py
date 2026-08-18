"""Tests for the Huawei LLDP neighbor adapter."""

from __future__ import annotations

from topo_semantic_adapter.adapters.base import AdapterContext
from topo_semantic_adapter.adapters.huawei.lldp import LldpNeighborParser


BRIEF_OUTPUT = """Local Intf        Neighbor Device ID        Neighbor Intf        Exptime
GE0/0/1           edge-sw-02                GE0/0/2              120
XG0/0/3           core-sw-03                XG0/0/4              110
"""


def test_parse_lldp_brief():
    parser = LldpNeighborParser()
    context = AdapterContext(device_ip="10.0.0.1", device_id="core-sw-01", site="site-a")
    entities = parser.parse("display lldp neighbor brief", BRIEF_OUTPUT, context)

    device_ids = {node.id for node in entities.nodes if node.kind == "device"}
    assert "core-sw-01:device:core-sw-01" in device_ids
    assert "edge-sw-02:device:edge-sw-02" in device_ids
    assert "core-sw-03:device:core-sw-03" in device_ids

    interface_ids = {node.id for node in entities.nodes if node.kind == "interface"}
    assert "core-sw-01:interface:GigabitEthernet0/0/1" in interface_ids
    assert "edge-sw-02:interface:GigabitEthernet0/0/2" in interface_ids
    assert "core-sw-01:interface:XGigabitEthernet0/0/3" in interface_ids
    assert "core-sw-03:interface:XGigabitEthernet0/0/4" in interface_ids

    edges = entities.edges
    assert len(edges) == 2
    assert all(edge.relation == "connects_to" for edge in edges)


VERBOSE_OUTPUT = """System Name: edge-sw-02
Port ID: GigabitEthernet0/0/2
Local Interface: GigabitEthernet0/0/1

System Name: core-sw-03
Port ID: XGigabitEthernet0/0/4
Local Intf: XGigabitEthernet0/0/3
"""


def test_parse_lldp_verbose_fallback():
    parser = LldpNeighborParser()
    context = AdapterContext(device_ip="10.0.0.1", device_id="core-sw-01", site="site-a")
    entities = parser.parse("display lldp neighbor verbose", VERBOSE_OUTPUT, context)

    device_ids = {node.id for node in entities.nodes if node.kind == "device"}
    assert "core-sw-01:device:core-sw-01" in device_ids
    assert "edge-sw-02:device:edge-sw-02" in device_ids
    assert "core-sw-03:device:core-sw-03" in device_ids

    interface_ids = {node.id for node in entities.nodes if node.kind == "interface"}
    assert "core-sw-01:interface:GigabitEthernet0/0/1" in interface_ids
    assert "edge-sw-02:interface:GigabitEthernet0/0/2" in interface_ids
    assert "core-sw-01:interface:XGigabitEthernet0/0/3" in interface_ids
    assert "core-sw-03:interface:XGigabitEthernet0/0/4" in interface_ids

    assert len(entities.edges) == 2


def test_parse_lldp_headers_only():
    parser = LldpNeighborParser()
    context = AdapterContext(device_ip="10.0.0.1", device_id="core-sw-01", site="site-a")
    output = "Local Intf        Neighbor Device ID        Neighbor Intf        Exptime\n"
    entities = parser.parse("display lldp neighbor brief", output, context)

    assert any(node.kind == "device" for node in entities.nodes)
    assert len(entities.edges) == 0


def test_parse_lldp_empty_output():
    parser = LldpNeighborParser()
    context = AdapterContext(device_ip="10.0.0.1", device_id="core-sw-01", site="site-a")
    entities = parser.parse("display lldp neighbor brief", "", context)

    assert any(node.id == "core-sw-01:device:core-sw-01" for node in entities.nodes)
    assert len(entities.edges) == 0


def test_parse_lldp_verbose_missing_local_intf_is_skipped():
    parser = LldpNeighborParser()
    context = AdapterContext(device_ip="10.0.0.1", device_id="core-sw-01", site="site-a")
    output = """System Name: edge-sw-02
Port ID: GigabitEthernet0/0/2
"""
    entities = parser.parse("display lldp neighbor verbose", output, context)

    # Local device is always emitted, but no neighbor edge without local intf.
    assert any(node.id == "core-sw-01:device:core-sw-01" for node in entities.nodes)
    assert len(entities.edges) == 0


NEIGHBOR_INFO_OUTPUT = """Local Interface: GE0/0/1
  System Name: edge-sw-02
  Port ID: GE0/0/2

Local Interface: XG0/0/3
  System Name: core-sw-03
  Port ID: XG0/0/4
"""


def test_parse_lldp_neighbor_information():
    parser = LldpNeighborParser()
    context = AdapterContext(device_ip="10.0.0.1", device_id="core-sw-01", site="site-a")
    entities = parser.parse("display lldp neighbor-information", NEIGHBOR_INFO_OUTPUT, context)

    device_ids = {node.id for node in entities.nodes if node.kind == "device"}
    assert "core-sw-01:device:core-sw-01" in device_ids
    assert "edge-sw-02:device:edge-sw-02" in device_ids
    assert "core-sw-03:device:core-sw-03" in device_ids

    interface_ids = {node.id for node in entities.nodes if node.kind == "interface"}
    assert "core-sw-01:interface:GigabitEthernet0/0/1" in interface_ids
    assert "edge-sw-02:interface:GigabitEthernet0/0/2" in interface_ids
    assert "core-sw-01:interface:XGigabitEthernet0/0/3" in interface_ids
    assert "core-sw-03:interface:XGigabitEthernet0/0/4" in interface_ids

    assert len(entities.edges) == 2


NEIGHBOR_INFO_VERBOSE_OUTPUT = """Local Interface: GigabitEthernet0/0/1
  System Name: edge-sw-02
  Port ID: GigabitEthernet0/0/2
  Port Description: Link to core

Local Interface: GigabitEthernet0/0/3
  System Name: core-sw-03
  Port ID: XGigabitEthernet0/0/4
"""


def test_parse_lldp_neighbor_information_verbose():
    parser = LldpNeighborParser()
    context = AdapterContext(device_ip="10.0.0.1", device_id="core-sw-01", site="site-a")
    entities = parser.parse(
        "display lldp neighbor-information verbose", NEIGHBOR_INFO_VERBOSE_OUTPUT, context
    )

    device_ids = {node.id for node in entities.nodes if node.kind == "device"}
    assert "core-sw-01:device:core-sw-01" in device_ids
    assert "edge-sw-02:device:edge-sw-02" in device_ids
    assert "core-sw-03:device:core-sw-03" in device_ids

    interface_ids = {node.id for node in entities.nodes if node.kind == "interface"}
    assert "core-sw-01:interface:GigabitEthernet0/0/1" in interface_ids
    assert "edge-sw-02:interface:GigabitEthernet0/0/2" in interface_ids
    assert "core-sw-01:interface:GigabitEthernet0/0/3" in interface_ids
    assert "core-sw-03:interface:XGigabitEthernet0/0/4" in interface_ids

    assert len(entities.edges) == 2


PLAIN_NEIGHBOR_OUTPUT = """System Name     Local Interface ChassisID      PortID       PortDescription
core-sw-01      GE0/0/1         xxxx-xxxx     GE0/0/1      Link to core
edge-sw-02      GE0/0/2         yyyy-yyyy     GE0/0/2      Link to edge
"""


def test_parse_lldp_neighbor_plain_table():
    parser = LldpNeighborParser()
    context = AdapterContext(device_ip="10.0.0.1", device_id="core-sw-01", site="site-a")
    entities = parser.parse("display lldp neighbor", PLAIN_NEIGHBOR_OUTPUT, context)

    device_ids = {node.id for node in entities.nodes if node.kind == "device"}
    assert "core-sw-01:device:core-sw-01" in device_ids
    assert "edge-sw-02:device:edge-sw-02" in device_ids

    interface_ids = {node.id for node in entities.nodes if node.kind == "interface"}
    assert "core-sw-01:interface:GigabitEthernet0/0/1" in interface_ids
    assert "edge-sw-02:interface:GigabitEthernet0/0/2" in interface_ids

    assert len(entities.edges) == 2


LOCAL_NEIGHBOR_INTF_OUTPUT = """Local Interface HelloTime Age TxExP RxExP Neighbor Interface
GE0/0/1         0         120 0       5       GE0/0/1
GE0/0/2         0         120 0       5       GE0/0/2
"""


def test_parse_lldp_neighbor_local_neighbor_intf_table():
    """``display lldp neighbor`` may expose only local+remote interface.

    Without a remote device name we cannot create a meaningful neighbor edge,
    so the adapter should only emit the local device anchor.
    """
    parser = LldpNeighborParser()
    context = AdapterContext(device_ip="10.0.0.1", device_id="core-sw-01", site="site-a")
    entities = parser.parse("display lldp neighbor", LOCAL_NEIGHBOR_INTF_OUTPUT, context)

    assert any(node.id == "core-sw-01:device:core-sw-01" for node in entities.nodes)
    assert len(entities.edges) == 0
