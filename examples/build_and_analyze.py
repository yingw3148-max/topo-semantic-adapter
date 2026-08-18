"""完整流程示例：从 CLI 巡检文件 -> TopoGraph -> 分析 -> 报告。

运行：
    python examples/build_and_analyze.py [site_dir]

默认使用测试夹具 ``tests/fixtures/湖北大学配置``。
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from toposphere_core.graph.export import export_mermaid
from toposphere_core.types import ExportOptions

# Allow running the example without installing the package in editable mode.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from topo_semantic_adapter import CLIFileLoader, GraphBuilder, generate_report
from topo_semantic_adapter.registry import AdapterRegistry


def main() -> None:
    parser = argparse.ArgumentParser(description="Build and analyze a TopoGraph from CLI files.")
    parser.add_argument(
        "site_dir",
        nargs="?",
        default=str(Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "湖北大学配置"),
        help="Path to the site directory (e.g. tests/fixtures/湖北大学配置).",
    )
    parser.add_argument(
        "--intent",
        default=None,
        help="Optional intent filter (e.g. fault_root_cause, impact_analysis).",
    )
    args = parser.parse_args()

    site_dir = Path(args.site_dir)
    if not site_dir.is_dir():
        raise SystemExit(f"Site directory does not exist: {site_dir}")

    site_name = site_dir.name
    base_path = site_dir.parent

    # 1. 加载 CLI 巡检文件
    print(f"\n[1/5] Loading CLI files from: {site_dir}\n")
    loader = CLIFileLoader(site_name=site_name, base_path=base_path)
    blocks = list(loader.iter_blocks())
    print(f"Found {len(blocks)} command/echo blocks.")

    # 2. 注册适配器并构建 TopoGraph
    print("\n[2/5] Building TopoGraph...")
    registry = AdapterRegistry()
    registry.load_builtin()
    builder = GraphBuilder(registry=registry, intent=args.intent, db_path=":memory:")
    builder.consume_many(blocks)
    graph = builder.build()
    print(f"Nodes: {graph.get_node_count()}, Edges: {graph.get_edge_count()}")

    # 3. 物化为 GraphView
    print("\n[3/5] Materializing GraphView...")
    view = graph.to_graphview()
    print(f"View nodes: {view.node_count()}, View edges: {view.edge_count()}")

    # 4. 导出多种 TopoGraph 视图
    print("\n[4/5] TopoGraph exports\n")

    print("--- summary ---")
    print(view.export(ExportOptions(format="summary", include_metadata=True)))

    print("\n--- skeleton ---")
    print(view.export(ExportOptions(format="skeleton", include_metadata=True)))

    print("\n--- mermaid ---")
    print(export_mermaid(view, title=f"{site_name} 拓扑"))

    # 5. 运行分析并输出报告
    print("\n[5/5] Analysis report\n")
    print(generate_report(graph))

    graph.close()


if __name__ == "__main__":
    main()
