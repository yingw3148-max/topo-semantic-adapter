"""Tests for building a ``toposphere_core.TopoGraph`` from CLI blocks."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

pytest.importorskip("toposphere_core")

from topo_semantic_adapter import CLIFileLoader, GraphBuilder
from topo_semantic_adapter.registry import AdapterRegistry
from topo_semantic_adapter.cli_loader import DEFAULT_DELIMITER

SAMPLE = f"""display link-aggregation verbose
Load-balance Type: Shar -- Load-balance, and NonS -- Non-Load-balance
Port Status: S -- Selected, U -- Unselected, I -- Individual
Local:
Interface Eth-Trunk1
PortName                      Status      Weight
GigabitEthernet0/0/1          Selected    1
GigabitEthernet0/0/2          Unselected  1
{DEFAULT_DELIMITER}
display version
VRP (R) software, Version 8.200
"""


def _make_loader(tmp: str) -> CLIFileLoader:
    site_name = "site-a"
    device_dir = Path(tmp) / f"{site_name}-配置" / "inspect" / "10.0.0.1_sw1"
    device_dir.mkdir(parents=True)
    (device_dir / "CommonCollectResult").write_text(SAMPLE, encoding="utf-8")
    return CLIFileLoader(site_name, tmp)


def test_graph_builder_populates_topograph():
    registry = AdapterRegistry()
    registry.load_builtin()

    with tempfile.TemporaryDirectory() as tmp:
        loader = _make_loader(tmp)
        blocks = list(loader.iter_blocks())

        builder = GraphBuilder(registry=registry, db_path=":memory:")
        builder.consume_many(blocks)
        graph = builder.build()

        assert graph.get_node_count() == 3  # 1 LAG group + 2 member interfaces
        assert graph.get_edge_count() == 2

        view = graph.to_graphview()
        assert view.node_count() == 3
        assert view.edge_count() == 2
        graph.close()


def test_graph_builder_filters_by_intent():
    registry = AdapterRegistry()
    registry.load_builtin()

    with tempfile.TemporaryDirectory() as tmp:
        loader = _make_loader(tmp)
        blocks = list(loader.iter_blocks())

        # impact_analysis should include link_aggregation; fault_root_cause should not.
        impact = GraphBuilder(registry=registry, intent="impact_analysis", db_path=":memory:")
        impact.consume_many(blocks)
        impact_graph = impact.build()
        assert impact_graph.get_node_count() == 3
        impact_graph.close()

        fault = GraphBuilder(registry=registry, intent="fault_root_cause", db_path=":memory:")
        fault.consume_many(blocks)
        fault_graph = fault.build()
        assert fault_graph.get_node_count() == 0
        fault_graph.close()


def test_graph_builder_reconstructs_lldp_topology():
    registry = AdapterRegistry()
    registry.load_builtin()

    lldp_a = f"""display lldp neighbor brief
Local Intf        Neighbor Device ID        Neighbor Intf        Exptime
GE0/0/1           edge-sw-02                GE0/0/2              120
"""
    lldp_b = f"""display lldp neighbor brief
Local Intf        Neighbor Device ID        Neighbor Intf        Exptime
GE0/0/2           core-sw-01                GE0/0/1              120
"""

    with tempfile.TemporaryDirectory() as tmp:
        site_name = "site-a"
        inspect = Path(tmp) / f"{site_name}-配置" / "inspect"

        dir_a = inspect / "10.0.0.1_core-sw-01"
        dir_a.mkdir(parents=True)
        (dir_a / "CommonCollectResult").write_text(lldp_a, encoding="utf-8")

        dir_b = inspect / "10.0.0.2_edge-sw-02"
        dir_b.mkdir(parents=True)
        (dir_b / "CommonCollectResult").write_text(lldp_b, encoding="utf-8")

        loader = CLIFileLoader(site_name, tmp)
        blocks = list(loader.iter_blocks())

        builder = GraphBuilder(registry=registry, db_path=":memory:")
        builder.consume_many(blocks)
        graph = builder.build()

        # 2 devices + 2 interfaces. Each interface appears once as the local
        # endpoint and once as the remote endpoint, but the deterministic ID
        # collapses them so we end up with 4 unique nodes and 2 directed edges.
        assert graph.get_node_count() == 4
        assert graph.get_edge_count() == 2

        view = graph.to_graphview()
        assert view.node_count() == 4
        assert view.edge_count() == 2
        graph.close()
