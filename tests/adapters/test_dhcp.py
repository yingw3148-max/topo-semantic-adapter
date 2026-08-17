"""Tests for the Huawei DHCP Snooping adapter."""

from __future__ import annotations

from topo_semantic_adapter.adapters.base import AdapterContext
from topo_semantic_adapter.adapters.huawei.dhcp import DhcpSnoopingParser


OUTPUT = """DHCP Snooping Bindings:
MAC Address     IP Address      Lease Time(seconds) Type       VLAN Interface
0001-0203-0405  10.1.1.10       86300               dhcp-snooping 10   GE0/0/1
0001-0203-0406  10.1.1.11       86000               dhcp-snooping 10   GigabitEthernet0/0/2
"""


def test_parse_dhcp_snooping():
    parser = DhcpSnoopingParser()
    context = AdapterContext(device_ip="10.0.0.1", device_id="edge-sw-02", site="site-a")
    entities = parser.parse("display dhcp snooping binding", OUTPUT, context)

    interfaces = {
        node.id: node.properties
        for node in entities.nodes
        if node.kind == "interface"
    }
    assert len(interfaces) == 2

    ge1 = interfaces["edge-sw-02:interface:GigabitEthernet0/0/1"]
    assert ge1["dhcp_lease_state"] == "bound"
    assert ge1["dhcp_bound_ip"] == "10.1.1.10"
    assert ge1["dhcp_bound_mac"] == "0001-0203-0405"
    assert ge1["dhcp_lease_time"] == 86300
    assert ge1["dhcp_vlan"] == "10"

    ge2 = interfaces["edge-sw-02:interface:GigabitEthernet0/0/2"]
    assert ge2["dhcp_bound_ip"] == "10.1.1.11"
