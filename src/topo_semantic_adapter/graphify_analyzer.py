"""graphify-style analysis pipeline for topology graphs.

This module wires the deterministic adapter output into graphify's build and
cluster stages, then adds a local-LLM semantic layer for Chinese community
labels and anomaly summaries. The final artifacts are written to
``graphify-out/graph.json`` and ``graphify-out/GRAPH_REPORT.md``.
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any

import networkx as nx
from toposphere_core import TopoGraph

from topo_semantic_adapter import CLIFileLoader, GraphBuilder
from topo_semantic_adapter.analysis import (
    analyze as topology_analyze,
    single_points_of_failure,
)
from topo_semantic_adapter.graphify_bridge import to_graphify_extractions
from topo_semantic_adapter.llm_client import LLMClient
from topo_semantic_adapter.registry import AdapterRegistry

# graphify is an optional dependency; these imports happen at call time via the
# run() function but the analyzer helpers below need them at module level.
from graphify.build import build  # noqa: E402
from graphify.cluster import cluster, label_communities_by_hub  # noqa: E402
from graphify.validate import assert_valid  # noqa: E402


def run(
    site_dir: Path,
    output_dir: Path,
    *,
    llm_client: LLMClient | None = None,
    intent: str | None = None,
    infer: bool = False,
) -> None:
    """Run the full graphify-style analysis for a site directory.

    Args:
        site_dir: Path to the site directory, e.g. ``tests/fixtures/湖北大学配置``.
        output_dir: Directory where ``graph.json`` and ``GRAPH_REPORT.md``
            will be written.
        llm_client: Optional LLM client for semantic enrichment. If ``None``,
            deterministic community labels are used.
        intent: Optional downstream intent passed to ``GraphBuilder``.
        infer: Whether to run second-pass topology inference.
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    # Phase 1: deterministic extraction into TopoGraph.
    site_name = site_dir.name
    base_path = site_dir.parent
    loader = CLIFileLoader(site_name=site_name, base_path=base_path)
    blocks = list(loader.iter_blocks())

    registry = AdapterRegistry()
    registry.load_builtin()
    builder = GraphBuilder(
        registry=registry,
        intent=intent,
        db_path=":memory:",
        infer=infer,
    )
    builder.consume_many(blocks)
    topo_graph = builder.build()

    # Phase 2: export to graphify schema.
    extractions = to_graphify_extractions(topo_graph, root=site_dir.parent)

    # Phase 3: graphify build + cluster.
    assert_valid(extractions)
    # Disable graphify's entity deduplication: in network topology, interfaces
    # on different devices (e.g. core GE0/0/1 and edge GE0/0/1) are distinct
    # entities even when they share a label.
    G = build([extractions], dedup=False)
    communities = cluster(G)

    # Phase 4: semantic enrichment via local LLM.
    community_labels = _label_communities(
        G, communities, llm_client=llm_client
    )

    # Phase 5: topology-specific analysis.
    topo_result = topology_analyze(topo_graph)
    anomaly_summary = _summarize_anomalies(topo_result, llm_client=llm_client)

    # Phase 6: export artifacts.
    _write_graph_json(output_dir / "graph.json", G, communities, community_labels)
    report = _generate_report(
        G,
        communities,
        community_labels,
        topo_result,
        anomaly_summary,
        root=site_dir,
    )
    (output_dir / "GRAPH_REPORT.md").write_text(report, encoding="utf-8")

    topo_graph.close()


def _label_communities(
    G: Any,
    communities: dict[int, list[str]],
    *,
    llm_client: LLMClient | None,
) -> dict[int, str]:
    """Return community labels, using LLM when available and deterministic hub labels otherwise."""
    hub_labels = label_communities_by_hub(G, communities)

    if llm_client is None:
        return hub_labels

    summaries: dict[int, str] = {}
    for cid, members in communities.items():
        lines: list[str] = []
        for node_id in members[:20]:
            attrs = G.nodes[node_id]
            kind = attrs.get("kind", "unknown")
            label = attrs.get("label", node_id)
            metadata = attrs.get("metadata", {})
            extras = ", ".join(
                f"{k}={v}" for k, v in metadata.items()
                if k not in ("confidence", "provenance") and v is not None
            )
            lines.append(f"- [{kind}] {label}" + (f" ({extras})" if extras else ""))
        summaries[cid] = "\n".join(lines)

    llm_labels = llm_client.label_communities(summaries)
    if llm_labels:
        return {cid: llm_labels.get(cid, hub_labels.get(cid, f"社区 {cid}")) for cid in communities}
    return hub_labels


def _summarize_anomalies(
    topo_result: dict[str, Any],
    *,
    llm_client: LLMClient | None,
) -> str:
    """Return a Chinese anomaly summary, optionally via LLM."""
    anomalies: list[dict[str, Any]] = []
    for node_id in topo_result.get("orphan_interfaces", []):
        anomalies.append({"type": "orphan_interface", "node_id": node_id})
    for item in topo_result.get("unhealthy_ospf", []):
        anomalies.append({"type": "unhealthy_ospf", **item})
    for item in topo_result.get("unselected_lag_members", []):
        anomalies.append({"type": "unselected_lag_member", **item})

    if not anomalies:
        return "未发现明显异常。"

    if llm_client is not None:
        summary = llm_client.summarize_anomalies(anomalies)
        if summary:
            return summary

    lines = ["发现以下异常信号："]
    for a in anomalies:
        if a["type"] == "orphan_interface":
            lines.append(f"- 孤立接口 `{a['node_id']}`")
        elif a["type"] == "unhealthy_ospf":
            lines.append(f"- 接口 `{a['node_id']}` 的 OSPF 状态为 {a.get('state')}")
        elif a["type"] == "unselected_lag_member":
            lines.append(
                f"- LAG 成员 `{a['interface_id']}` 未选中（状态：{a.get('selected_status')}）"
            )
    return "\n".join(lines)


def _write_graph_json(
    path: Path,
    G: Any,
    communities: dict[int, list[str]],
    community_labels: dict[int, str],
) -> None:
    """Serialize the NetworkX graph plus community metadata to JSON."""
    from networkx.readwrite import json_graph

    data = json_graph.node_link_data(G)
    data["communities"] = {
        str(cid): {
            "label": community_labels.get(cid, f"Community {cid}"),
            "nodes": nodes,
        }
        for cid, nodes in communities.items()
    }
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _generate_report(
    G: Any,
    communities: dict[int, list[str]],
    community_labels: dict[int, str],
    topo_result: dict[str, Any],
    anomaly_summary: str,
    root: Path,
) -> str:
    """Generate a Chinese graphify-style Markdown report for network topology."""
    spof = topo_result["single_points_of_failure"]

    node_count = G.number_of_nodes()
    edge_count = G.number_of_edges()
    density = nx.density(G) if node_count > 1 else 0.0
    avg_degree = round(2 * edge_count / node_count, 4) if node_count else 0.0

    node_kind_counts: dict[str, int] = defaultdict(int)
    for _, attrs in G.nodes(data=True):
        node_kind_counts[str(attrs.get("kind", "unknown"))] += 1

    edge_kind_counts: dict[str, int] = defaultdict(int)
    for _, _, attrs in G.edges(data=True):
        edge_kind_counts[str(attrs.get("relation", "unknown"))] += 1

    lines: list[str] = [
        f"# Graph Report - {root.name}",
        "",
        "## 概要",
        f"- 节点数: {node_count}",
        f"- 边数: {edge_count}",
        f"- 密度: {round(density, 4)}",
        f"- 平均度: {avg_degree}",
        f"- 社区数: {len(communities)}",
        "- 节点类型分布:",
    ]
    for kind, count in sorted(node_kind_counts.items()):
        lines.append(f"  - {kind}: {count}")
    lines.append("- 边类型分布:")
    for kind, count in sorted(edge_kind_counts.items()):
        lines.append(f"  - {kind}: {count}")

    lines.extend(["", "## 数据来源（可解释性）"])
    lines.append("- 边置信度分布:")
    for conf, count in topo_result["confidence_distribution"].items():
        lines.append(f"  - {conf}: {count}")
    lines.append("- Parser 贡献次数:")
    for producer, count in topo_result["provenance_summary"].items():
        lines.append(f"  - {producer}: {count}")

    lines.extend(["", "## 关键节点（度中心性 Top）"])
    top_nodes = sorted(G.degree(), key=lambda item: item[1], reverse=True)[:10]
    for node_id, degree in top_nodes:
        label = G.nodes[node_id].get("label", node_id)
        lines.append(f"- `{label}`: degree {degree}")

    lines.extend(["", "## 社区划分"])
    for cid, members in communities.items():
        label = community_labels.get(cid, f"社区 {cid}")
        lines.append(f"- {label}: {len(members)} 个节点")

    lines.extend(["", "## 单点故障风险"])
    lines.append(f"- 桥接边: {len(spof['bridges'])}")
    for bridge in spof["bridges"]:
        lines.append(f"  - `{bridge['edge_id']}`")
    lines.append(f"- 割点: {len(spof['articulation_points'])}")
    for point in spof["articulation_points"]:
        lines.append(f"  - `{point['node_id']}`")

    lines.extend(["", "## 异常信号"])
    lines.append(anomaly_summary)

    lines.append("")
    return "\n".join(lines)
