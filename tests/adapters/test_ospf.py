"""Tests for the Huawei OSPF neighbor adapter."""

from __future__ import annotations

from topo_semantic_adapter.adapters.base import AdapterContext
from topo_semantic_adapter.adapters.huawei.ospf import OspfNeighborParser


OUTPUT = """OSPF Process 1 with Router ID 1.1.1.1

 Area 0.0.0.0 interface 10.1.1.1(GigabitEthernet0/0/1)'s neighbors
 Router ID: 2.2.2.2          Address: 10.1.1.2
   State: Full           Mode:Nbr is Master           Priority: 1
   DR: 10.1.1.1          BDR: 10.1.1.2          MTU: 0

 Area 0.0.0.0 interface 10.1.1.5(GE0/0/2)'s neighbors
 Router ID: 3.3.3.3          Address: 10.1.1.6
   State: Init           Mode:Nbr is Slave            Priority: 1
"""


def test_parse_ospf_neighbors():
    parser = OspfNeighborParser()
    context = AdapterContext(device_ip="10.0.0.1", device_id="core-sw-01", site="site-a")
    entities = parser.parse("display ospf peer", OUTPUT, context)

    interfaces = {
        node.id: node.properties
        for node in entities.nodes
        if node.kind == "interface"
    }
    assert len(interfaces) == 2

    ge1 = interfaces["core-sw-01:interface:GigabitEthernet0/0/1"]
    assert ge1["ospf_neighbor_state"] == "Full"
    assert ge1["ospf_neighbor_router_id"] == "2.2.2.2"

    ge2 = interfaces["core-sw-01:interface:GigabitEthernet0/0/2"]
    assert ge2["ospf_neighbor_state"] == "Init"
    assert ge2["ospf_neighbor_router_id"] == "3.3.3.3"
