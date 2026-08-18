"""Tests for the topology analysis pipeline."""

from __future__ import annotations

from topo_semantic_adapter import CLIFileLoader, GraphBuilder
from topo_semantic_adapter.analysis import (
    analyze,
    communities,
    generate_report,
    god_nodes,
    graph_summary,
    orphan_interfaces,
    single_points_of_failure,
    to_graphview,
    unhealthy_ospf,
    unselected_lag_members,
)
from topo_semantic_adapter.registry import AdapterRegistry
from tests.fixtures import write_fixture_site


def _build_sample_graph(tmp_path):
    site_dir = write_fixture_site(tmp_path)
    loader = CLIFileLoader(site_name="湖北大学配置", base_path=site_dir.parent)
    blocks = list(loader.iter_blocks())

    registry = AdapterRegistry()
    registry.load_builtin()
    builder = GraphBuilder(registry=registry, db_path=":memory:")
    builder.consume_many(blocks)
    return builder.build()


def test_to_graphview(tmp_path):
    graph = _build_sample_graph(tmp_path)
    view = to_graphview(graph)
    assert view.node_count() == 9
    assert view.edge_count() == 5


def test_graph_summary(tmp_path):
    graph = _build_sample_graph(tmp_path)
    summary = graph_summary(to_graphview(graph))
    assert summary["node_count"] == 9
    assert summary["edge_count"] == 5
    assert summary["node_count_by_kind"]["interface"] == 5
    assert summary["node_count_by_kind"]["device"] == 2
    assert summary["edge_count_by_kind"]["connects_to"] == 2
    assert summary["edge_count_by_kind"]["member_of"] == 3


def test_god_nodes(tmp_path):
    graph = _build_sample_graph(tmp_path)
    top = god_nodes(to_graphview(graph), top_n=3)
    assert len(top) == 3
    # Degree is non-increasing.
    assert top[0][1] >= top[1][1] >= top[2][1]


def test_communities(tmp_path):
    graph = _build_sample_graph(tmp_path)
    groups = communities(to_graphview(graph))
    assert len(groups) >= 1
    # Every node belongs to exactly one community.
    total = sum(len(members) for members in groups.values())
    assert total == 9


def test_single_points_of_failure(tmp_path):
    graph = _build_sample_graph(tmp_path)
    spof = single_points_of_failure(to_graphview(graph))

    # The three LAG member edges are leaf bridges (each connects a single
    # interface to its aggregation group).
    bridge_ids = {b["edge_id"] for b in spof["bridges"]}
    assert len(bridge_ids) == 3
    assert all("member-of" in edge_id for edge_id in bridge_ids)

    # The core Eth-Trunk1 group is an articulation point: removing it would
    # disconnect GE0/0/2 and GE0/0/3 from the rest of the graph.
    articulation_ids = {ap["node_id"] for ap in spof["articulation_points"]}
    assert "core-sw-01:link_aggregation_group:Eth-Trunk1" in articulation_ids


def test_orphan_interfaces(tmp_path):
    graph = _build_sample_graph(tmp_path)
    orphans = orphan_interfaces(to_graphview(graph))
    assert orphans == []


def test_unhealthy_ospf(tmp_path):
    graph = _build_sample_graph(tmp_path)
    bad = unhealthy_ospf(to_graphview(graph))
    assert bad == []


def test_unselected_lag_members(tmp_path):
    graph = _build_sample_graph(tmp_path)
    members = unselected_lag_members(to_graphview(graph))
    assert len(members) == 1
    assert members[0]["interface_id"] == "core-sw-01:interface:GigabitEthernet0/0/3"
    assert members[0]["selected_status"] == "Unselected"


def test_analyze_returns_all_sections(tmp_path):
    graph = _build_sample_graph(tmp_path)
    result = analyze(graph)
    assert set(result) == {
        "summary",
        "god_nodes",
        "communities",
        "single_points_of_failure",
        "orphan_interfaces",
        "unhealthy_ospf",
        "unselected_lag_members",
        "confidence_distribution",
        "provenance_summary",
    }


def test_generate_report_contains_key_sections(tmp_path):
    graph = _build_sample_graph(tmp_path)
    report = generate_report(graph)
    assert "# 拓扑分析报告" in report
    assert "## 概要" in report
    assert "## 关键节点" in report
    assert "## 社区划分" in report
    assert "## 单点故障风险" in report
    assert "## 异常信号" in report
