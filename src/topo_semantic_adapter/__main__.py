"""CLI entry point for topo-semantic-adapter.

Usage:
    python -m topo_semantic_adapter analyze <site_dir> [--intent INTENT]
    python -m topo_semantic_adapter graphify <site_dir> [--output DIR]
    topo-semantic-adapter analyze <site_dir> [--intent INTENT]
    topo-semantic-adapter graphify <site_dir> [--output DIR]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from toposphere_core.graph.export import export_mermaid
from toposphere_core.types import ExportOptions

from topo_semantic_adapter import CLIFileLoader, GraphBuilder, generate_report
from topo_semantic_adapter.graphify_analyzer import run as run_graphify
from topo_semantic_adapter.llm_client import LLMClient
from topo_semantic_adapter.registry import AdapterRegistry


def _add_common_args(parser: argparse.ArgumentParser) -> None:
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
        "--infer",
        action="store_true",
        help="Run second-pass inference to reconstruct missing topology nodes/edges.",
    )


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="topo-semantic-adapter",
        description="Translate CLI inspection files into a topology graph and report.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # --- analyze (default/legacy behavior) ---
    analyze_parser = subparsers.add_parser(
        "analyze",
        help="Build a topology graph and print an analysis report.",
    )
    _add_common_args(analyze_parser)
    analyze_parser.add_argument(
        "--no-validate",
        action="store_true",
        help="Disable parser-output schema validation (not recommended).",
    )
    analyze_parser.add_argument(
        "--format",
        default="report",
        choices=["report", "summary", "skeleton", "mermaid"],
        help="Output format. 'report' prints the full analysis report.",
    )

    # --- graphify (graphify-style pipeline) ---
    graphify_parser = subparsers.add_parser(
        "graphify",
        help="Run a graphify-style pipeline: build, cluster, report, export graph.json.",
    )
    _add_common_args(graphify_parser)
    graphify_parser.add_argument(
        "--output",
        default="graphify-out",
        help="Output directory for graph.json and GRAPH_REPORT.md (default: graphify-out).",
    )
    graphify_parser.add_argument(
        "--llm-base-url",
        default=None,
        help="OpenAI-compatible base URL for the local LLM (default: env OPENAI_BASE_URL or http://localhost:11434/v1).",
    )
    graphify_parser.add_argument(
        "--llm-model",
        default=None,
        help="Model name for the local LLM (default: env OPENAI_MODEL or qwen2.5-coder:7b).",
    )
    graphify_parser.add_argument(
        "--no-llm",
        action="store_true",
        help="Skip LLM enrichment and use deterministic community labels.",
    )

    return parser


def _cmd_analyze(args: argparse.Namespace) -> int:
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
        infer=args.infer,
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


def _cmd_graphify(args: argparse.Namespace) -> int:
    site_dir = Path(args.site_dir)
    if not site_dir.is_dir():
        print(f"Error: site directory does not exist: {site_dir}", file=sys.stderr)
        return 1

    llm_client: LLMClient | None = None
    if not args.no_llm:
        try:
            llm_client = LLMClient(
                base_url=args.llm_base_url,
                model=args.llm_model,
            )
        except RuntimeError as exc:
            print(f"[graphify] {exc}; continuing without LLM enrichment.", file=sys.stderr)

    run_graphify(
        site_dir=site_dir,
        output_dir=Path(args.output),
        llm_client=llm_client,
        intent=args.intent,
        infer=args.infer,
    )
    print(f"graphify output written to {args.output}/")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_arg_parser()
    args_list = list(argv) if argv is not None else sys.argv[1:]

    # Backward compatibility: legacy usage omits the subcommand and starts with
    # the site directory. Default to the "analyze" subcommand in that case.
    commands = {"analyze", "graphify", "-h", "--help"}
    if args_list and args_list[0] not in commands:
        args_list.insert(0, "analyze")

    args = parser.parse_args(args_list)

    if args.command == "analyze":
        return _cmd_analyze(args)
    if args.command == "graphify":
        return _cmd_graphify(args)

    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
