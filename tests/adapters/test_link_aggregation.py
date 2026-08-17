"""Tests for the Huawei link-aggregation adapter."""

from __future__ import annotations

from topo_semantic_adapter.adapters.base import AdapterContext
from topo_semantic_adapter.adapters.huawei.link_aggregation import LinkAggregationParser


OUTPUT = """Load-balance Type: Shar -- Load-balance, and NonS -- Non-Load-balance
Port Status: S -- Selected, U -- Unselected, I -- Individual
Local:
Totalnumberof trunk members: 3
Number of active members: 2
Interface Eth-Trunk1
PortName                      Status      Weight
GigabitEthernet0/0/1          Selected    1
GigabitEthernet0/0/2          Unselected  1
Interface Eth-Trunk2
PortName                      Status      Weight
XGigabitEthernet0/0/3         S           1
40GE0/0/4                     I           1
"""


def test_parse_link_aggregation():
    parser = LinkAggregationParser()
    context = AdapterContext(device_ip="10.0.0.1", device_id="sw1", site="site-a")
    entities = parser.parse("display link-aggregation verbose", OUTPUT, context)

    groups = {
        node.properties["name"]
        for node in entities.nodes
        if node.kind == "link_aggregation_group"
    }
    assert groups == {"Eth-Trunk1", "Eth-Trunk2"}

    members = {
        (edge.source, edge.properties["selected_status"])
        for edge in entities.edges
        if edge.relation == "member_of"
    }
    expected = {
        ("sw1:interface:GigabitEthernet0/0/1", "Selected"),
        ("sw1:interface:GigabitEthernet0/0/2", "Unselected"),
        ("sw1:interface:XGigabitEthernet0/0/3", "Selected"),
        ("sw1:interface:40GE0/0/4", "Individual"),
    }
    assert members == expected


def test_parse_link_aggregation_empty_output():
    parser = LinkAggregationParser()
    context = AdapterContext(device_ip="10.0.0.1", device_id="sw1", site="site-a")
    entities = parser.parse("display link-aggregation verbose", "", context)

    assert len(entities.nodes) == 0
    assert len(entities.edges) == 0


def test_parse_link_aggregation_no_group_header():
    parser = LinkAggregationParser()
    context = AdapterContext(device_ip="10.0.0.1", device_id="sw1", site="site-a")
    entities = parser.parse(
        "display link-aggregation verbose",
        "PortName                      Status      Weight\nGigabitEthernet0/0/1          Selected    1\n",
        context,
    )

    assert len(entities.nodes) == 0
    assert len(entities.edges) == 0
