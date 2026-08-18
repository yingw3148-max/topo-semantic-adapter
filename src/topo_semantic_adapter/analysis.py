"""Topology analysis helpers inspired by the graphify pipeline.

This module treats the adapter's output ``TopoGraph`` as the input to a small
analysis pipeline:

    TopoGraph -> GraphView -> summary / communities / centrality / risks -> report

It reuses the algorithms already provided by ``toposphere_core`` rather than
introducing a new graph library dependency.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from toposphere_core import TopoGraph
from toposphere_core.types import GraphView, kind_value


def to_graphview(graph: TopoGraph) -> GraphView:
    """Materialize a persistent ``TopoGraph`` into an in-memory ``GraphView``."""
    return graph.to_graphview()


def graph_summary(view: GraphView) -> dict[str, Any]:
    """Return a plain-dict summary of the view."""
    summary = view.summary()
    return {
        "node_count": summary.node_count,
        "edge_count": summary.edge_count,
        "density": round(summary.density, 4),
        "average_degree": round(summary.average_degree, 4),
        "node_count_by_kind": dict(summary.node_count_by_kind),
        "edge_count_by_kind": dict(summary.edge_count_by_kind),
    }


def god_nodes(view: GraphView, top_n: int = 5) -> list[tuple[str, float]]:
    """Return the top-N nodes by degree centrality ("god nodes")."""
    scores = view.centrality(metric="degree").scores
    return sorted(scores.items(), key=lambda item: item[1], reverse=True)[:top_n]


def communities(view: GraphView) -> dict[int, list[str]]:
    """Group node IDs by detected community."""
    mapping = view.communities()
    groups: dict[int, list[str]] = defaultdict(list)
    for node_id, community_id in mapping.items():
        groups[community_id].append(node_id)
    return dict(groups)


def single_points_of_failure(view: GraphView) -> dict[str, Any]:
    """Find bridge edges and articulation points in the topology."""
    return {
        "bridges": [
            {"edge_id": bridge.edge.id, "split_count": bridge.split_count}
            for bridge in view.bridges()
        ],
        "articulation_points": [
            {"node_id": point.node.id, "split_count": point.split_count}
            for point in view.articulation_points()
        ],
    }


def orphan_interfaces(view: GraphView) -> list[str]:
    """Return interface nodes with no incident edges."""
    orphan_ids: list[str] = []
    for node_id, node in view.nodes.items():
        if kind_value(node.kind) != "interface":
            continue
        if not view.get_outgoing_edges(node_id) and not view.get_incoming_edges(node_id):
            orphan_ids.append(node_id)
    return orphan_ids


def unhealthy_ospf(view: GraphView) -> list[dict[str, Any]]:
    """List interfaces whose OSPF neighbor state is present but not Full."""
    result: list[dict[str, Any]] = []
    for node in view.nodes.values():
        if kind_value(node.kind) != "interface":
            continue
        state = node.metadata.get("ospf_neighbor_state")
        if state and state != "Full":
            result.append({"node_id": node.id, "state": state})
    return result


def unselected_lag_members(view: GraphView) -> list[dict[str, Any]]:
    """List LAG member edges whose ``selected_status`` is Unselected."""
    result: list[dict[str, Any]] = []
    for edge in view.edges:
        if kind_value(edge.kind) != "member_of":
            continue
        status = edge.metadata.get("selected_status")
        if status == "Unselected":
            result.append(
                {
                    "interface_id": edge.source,
                    "lag_id": edge.target,
                    "selected_status": status,
                }
            )
    return result


def confidence_distribution(view: GraphView) -> dict[str, int]:
    """Count edges by confidence label (EXTRACTED / INFERRED / AMBIGUOUS)."""
    counts: dict[str, int] = defaultdict(int)
    for edge in view.edges:
        counts[edge.metadata.get("confidence", "EXTRACTED")] += 1
    return dict(counts)


def provenance_summary(view: GraphView) -> dict[str, int]:
    """Count how many times each producer/parser contributed to the graph."""
    counts: dict[str, int] = defaultdict(int)
    for node in view.nodes.values():
        for prov in node.provenance:
            if prov.producer:
                counts[prov.producer] += 1
    for edge in view.edges:
        for prov in edge.provenance:
            if prov.producer:
                counts[prov.producer] += 1
    return dict(counts)


def analyze(graph: TopoGraph) -> dict[str, Any]:
    """Run the full analysis pipeline and return a plain dict."""
    view = to_graphview(graph)
    return {
        "summary": graph_summary(view),
        "god_nodes": god_nodes(view),
        "communities": communities(view),
        "single_points_of_failure": single_points_of_failure(view),
        "orphan_interfaces": orphan_interfaces(view),
        "unhealthy_ospf": unhealthy_ospf(view),
        "unselected_lag_members": unselected_lag_members(view),
        "confidence_distribution": confidence_distribution(view),
        "provenance_summary": provenance_summary(view),
    }


def generate_report(graph: TopoGraph) -> str:
    """Generate a Markdown analysis report from a ``TopoGraph``."""
    result = analyze(graph)
    summary = result["summary"]
    spof = result["single_points_of_failure"]

    lines: list[str] = [
        "# 拓扑分析报告",
        "",
        "## 概要",
        f"- 节点数: {summary['node_count']}",
        f"- 边数: {summary['edge_count']}",
        f"- 密度: {summary['density']}",
        f"- 平均度: {summary['average_degree']}",
        "- 节点类型分布:",
    ]
    for kind, count in summary["node_count_by_kind"].items():
        lines.append(f"  - {kind}: {count}")
    lines.append("- 边类型分布:")
    for kind, count in summary["edge_count_by_kind"].items():
        lines.append(f"  - {kind}: {count}")

    lines.extend(["", "## 数据来源（可解释性）"])
    lines.append("- 边置信度分布:")
    for conf, count in result["confidence_distribution"].items():
        lines.append(f"  - {conf}: {count}")
    lines.append("- Parser 贡献次数:")
    for producer, count in result["provenance_summary"].items():
        lines.append(f"  - {producer}: {count}")

    lines.extend(["", "## 关键节点（度中心性 Top）"])
    for node_id, score in result["god_nodes"]:
        lines.append(f"- `{node_id}`: degree {score}")

    lines.extend(["", "## 社区划分"])
    for community_id, members in result["communities"].items():
        lines.append(f"- 社区 {community_id}: {len(members)} 个节点")

    lines.extend(["", "## 单点故障风险"])
    lines.append(f"- 桥接边: {len(spof['bridges'])}")
    for bridge in spof["bridges"]:
        lines.append(f"  - `{bridge['edge_id']}` (split_count={bridge['split_count']})")
    lines.append(f"- 割点: {len(spof['articulation_points'])}")
    for point in spof["articulation_points"]:
        lines.append(
            f"  - `{point['node_id']}` (split_count={point['split_count']})"
        )

    lines.extend(["", "## 异常信号"])
    lines.append(f"- 孤立接口: {len(result['orphan_interfaces'])}")
    for node_id in result["orphan_interfaces"]:
        lines.append(f"  - `{node_id}`")
    lines.append(f"- 不健康的 OSPF 邻居: {len(result['unhealthy_ospf'])}")
    for item in result["unhealthy_ospf"]:
        lines.append(f"  - `{item['node_id']}`: state={item['state']}")
    lines.append(f"- 未选中的 LAG 成员: {len(result['unselected_lag_members'])}")
    for item in result["unselected_lag_members"]:
        lines.append(f"  - `{item['interface_id']}` -> `{item['lag_id']}`")

    lines.append("")
    return "\n".join(lines)
