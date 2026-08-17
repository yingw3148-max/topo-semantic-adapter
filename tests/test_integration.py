"""End-to-end integration tests using real CLI fixture files."""

from __future__ import annotations

from topo_semantic_adapter import CLIFileLoader, GraphBuilder
from topo_semantic_adapter.registry import AdapterRegistry


def test_fixture_site_builds_topograph(fixture_site_path):
    """A real two-device fixture should produce a merged topology graph."""
    registry = AdapterRegistry()
    registry.load_builtin()

    loader = CLIFileLoader(site_name="湖北大学配置", base_path=fixture_site_path.parent)
    blocks = list(loader.iter_blocks())
    assert len(blocks) == 9  # 5 from core + 4 from edge

    builder = GraphBuilder(registry=registry, db_path=":memory:")
    builder.consume_many(blocks)
    graph = builder.build()

    # 2 devices + 5 unique interfaces + 2 LAG groups.
    # GE0/0/1 appears on both devices and is linked by LLDP.
    assert graph.get_node_count() == 9
    assert graph.get_edge_count() == 5  # 2 LLDP + 3 LAG member edges

    view = graph.to_graphview()
    assert view.node_count() == 9
    assert view.edge_count() == 5

    # LLDP merged GE0/0/1 on both devices; it should carry OSPF and VRRP
    # properties from core, plus DHCP from edge.
    core_ge1 = view.get_node_by_id("core-sw-01:interface:GigabitEthernet0/0/1")
    assert core_ge1 is not None
    assert core_ge1.metadata["ospf_neighbor_state"] == "Full"
    assert core_ge1.metadata["vrrp_role_state"] == "Master"

    edge_ge1 = view.get_node_by_id("edge-sw-02:interface:GigabitEthernet0/0/1")
    assert edge_ge1 is not None
    assert edge_ge1.metadata["vrrp_role_state"] == "Backup"
    assert edge_ge1.metadata["dhcp_bound_ip"] == "10.1.2.11"

    graph.close()


def test_fixture_site_with_fault_root_cause_intent(fixture_site_path):
    """fault_root_cause should keep LLDP, OSPF, DHCP and drop LAG/VRRP."""
    registry = AdapterRegistry()
    registry.load_builtin()

    loader = CLIFileLoader(site_name="湖北大学配置", base_path=fixture_site_path.parent)
    blocks = list(loader.iter_blocks())

    builder = GraphBuilder(
        registry=registry, intent="fault_root_cause", db_path=":memory:"
    )
    builder.consume_many(blocks)
    graph = builder.build()

    # LLDP produces 2 devices + 2 interfaces, OSPF enriches core GE0/0/1,
    # DHCP enriches edge GE0/0/1 and creates core GE0/0/2.
    assert graph.get_node_count() == 5
    assert graph.get_edge_count() == 2
    graph.close()


def test_fixture_site_with_impact_analysis_intent(fixture_site_path):
    """impact_analysis should keep LLDP, LAG, VRRP and drop OSPF/DHCP."""
    registry = AdapterRegistry()
    registry.load_builtin()

    loader = CLIFileLoader(site_name="湖北大学配置", base_path=fixture_site_path.parent)
    blocks = list(loader.iter_blocks())

    builder = GraphBuilder(
        registry=registry, intent="impact_analysis", db_path=":memory:"
    )
    builder.consume_many(blocks)
    graph = builder.build()

    # 2 devices + 5 interfaces + 2 LAG groups.
    assert graph.get_node_count() == 9
    # 2 LLDP + 3 LAG member edges.
    assert graph.get_edge_count() == 5
    graph.close()
