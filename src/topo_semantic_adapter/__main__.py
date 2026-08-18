"""CLI entry point for topo-semantic-adapter.

Usage:
    python -m topo_semantic_adapter <site_dir> [--intent INTENT]
    topo-semantic-adapter <site_dir> [--intent INTENT]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from toposphere_core.graph.export import export_mermaid
from toposphere_core.types import ExportOptions

from topo_semantic_adapter import CLIFileLoader, GraphBuilder, generate_report
from topo_semantic_adapter.registry import AdapterRegistry


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="topo-semantic-adapter",
        description="Translate CLI inspection files into a topology graph and report.",
    )
    parser.add_argument(
        "site_dir",
        help="Path to the site directory, e.g. /data/sites/湖北大学配置.",
    )
    parser.add_argument(
        "--intent",
        default=None,
        choices=["fault_root_cause", "impact_analysis"],
        help="Optional downstream intent to filter which attributes are mounted.",
    )
    parser.add_argument(
        "--no-validate",
        action="store_true",
        help="Disable parser-output schema validation (not recommended).",
    )
    parser.add_argument(
        "--format",
        default="report",
        choices=["report", "summary", "skeleton", "mermaid"],
        help="Output format. 'report' prints the full analysis report.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    site_dir = Path(args.site_dir)
    if not site_dir.is_dir():
        print(f"Error: site directory does not exist: {site_dir}", file=sys.stderr)
        return 1

    site_name = site_dir.name
    base_path = site_dir.parent

    loader = CLIFileLoader(site_name=site_name, base_path=base_path)
    blocks = list(loader.iter_blocks())
    if not blocks:
        print(f"Warning: no command blocks found under {site_dir}", file=sys.stderr)
        return 0

    registry = AdapterRegistry()
    registry.load_builtin()
    builder = GraphBuilder(
        registry=registry,
        intent=args.intent,
        db_path=":memory:",
        validate=not args.no_validate,
    )
    builder.consume_many(blocks)
    graph = builder.build()

    try:
        if args.format == "report":
            print(generate_report(graph))
        else:
            view = graph.to_graphview()
            if args.format == "summary":
                print(view.export(ExportOptions(format="summary", include_metadata=True)))
            elif args.format == "skeleton":
                print(view.export(ExportOptions(format="skeleton", include_metadata=True)))
            elif args.format == "mermaid":
                print(export_mermaid(view, title=f"{site_name} 拓扑"))
    finally:
        graph.close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
