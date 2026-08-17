"""Tests for the Huawei VRRP adapter."""

from __future__ import annotations

from topo_semantic_adapter.adapters.base import AdapterContext
from topo_semantic_adapter.adapters.huawei.vrrp import VrrpParser


OUTPUT = """GigabitEthernet0/0/1 | Virtual Router 1
    State: Master
    Virtual IP: 10.1.1.254
    Master IP: 10.1.1.1
GE0/0/2 | Virtual Router 2
    State: Backup
    Virtual IP: 10.1.2.254
"""


def test_parse_vrrp():
    parser = VrrpParser()
    context = AdapterContext(device_ip="10.0.0.1", device_id="core-sw-01", site="site-a")
    entities = parser.parse("display vrrp", OUTPUT, context)

    interfaces = {
        node.id: node.properties
        for node in entities.nodes
        if node.kind == "interface"
    }
    assert len(interfaces) == 2

    ge1 = interfaces["core-sw-01:interface:GigabitEthernet0/0/1"]
    assert ge1["vrrp_role_state"] == "Master"
    assert ge1["vrrp_vrid"] == "1"
    assert ge1["vrrp_virtual_ip"] == "10.1.1.254"

    ge2 = interfaces["core-sw-01:interface:GigabitEthernet0/0/2"]
    assert ge2["vrrp_role_state"] == "Backup"
    assert ge2["vrrp_vrid"] == "2"
    assert ge2["vrrp_virtual_ip"] == "10.1.2.254"


def test_parse_vrrp_missing_virtual_ip():
    parser = VrrpParser()
    context = AdapterContext(device_ip="10.0.0.1", device_id="core-sw-01", site="site-a")
    output = """GigabitEthernet0/0/1 | Virtual Router 10
    State: Master
"""
    entities = parser.parse("display vrrp", output, context)

    properties = entities.nodes[0].properties
    assert properties["vrrp_role_state"] == "Master"
    assert properties["vrrp_vrid"] == "10"
    assert properties["vrrp_virtual_ip"] == ""
