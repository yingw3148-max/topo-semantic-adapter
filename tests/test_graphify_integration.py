"""Tests for the graphify integration pipeline."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

pytest.importorskip("toposphere_core")
graphify = pytest.importorskip("graphify")

from topo_semantic_adapter import CLIFileLoader, GraphBuilder
from topo_semantic_adapter.graphify_analyzer import run as run_graphify
from topo_semantic_adapter.graphify_bridge import to_graphify_extractions
from topo_semantic_adapter.llm_client import LLMClient
from topo_semantic_adapter.registry import AdapterRegistry


def _build_topograph(site_path: Path):
    loader = CLIFileLoader(site_name=site_path.name, base_path=site_path.parent)
    blocks = list(loader.iter_blocks())
    registry = AdapterRegistry()
    registry.load_builtin()
    builder = GraphBuilder(registry=registry, db_path=":memory:")
    builder.consume_many(blocks)
    return builder.build()


def test_graphify_bridge_exports_valid_schema(fixture_site_path):
    topo_graph = _build_topograph(fixture_site_path)
    try:
        extractions = to_graphify_extractions(topo_graph, root=fixture_site_path.parent)
        from graphify.validate import validate_extraction

        errors = validate_extraction(extractions)
        assert errors == [], f"schema errors: {errors}"
        assert extractions["nodes"]
        assert extractions["edges"]
    finally:
        topo_graph.close()


def test_graphify_pipeline_runs_without_llm(fixture_site_path, tmp_path):
    output_dir = tmp_path / "graphify-out"
    run_graphify(
        site_dir=fixture_site_path,
        output_dir=output_dir,
        llm_client=None,
    )

    graph_json = output_dir / "graph.json"
    report_md = output_dir / "GRAPH_REPORT.md"
    assert graph_json.is_file()
    assert report_md.is_file()

    data = json.loads(graph_json.read_text(encoding="utf-8"))
    assert "nodes" in data
    assert "edges" in data
    assert "communities" in data

    report = report_md.read_text(encoding="utf-8")
    assert "# Graph Report" in report
    assert "## 社区划分" in report


def test_graphify_pipeline_with_mock_llm(fixture_site_path, tmp_path):
    mock_llm = MagicMock(spec=LLMClient)
    mock_llm.label_communities.return_value = {0: "核心层", 1: "边缘层"}
    mock_llm.summarize_anomalies.return_value = "未发现明显异常。"

    output_dir = tmp_path / "graphify-out"
    run_graphify(
        site_dir=fixture_site_path,
        output_dir=output_dir,
        llm_client=mock_llm,
    )

    report = (output_dir / "GRAPH_REPORT.md").read_text(encoding="utf-8")
    assert "核心层" in report or "边缘层" in report
    mock_llm.label_communities.assert_called_once()


def test_graphify_cli_subcommand(fixture_site_path, tmp_path, capsys):
    from topo_semantic_adapter.__main__ import main

    output_dir = tmp_path / "graphify-out"
    rc = main(
        [
            "graphify",
            str(fixture_site_path),
            "--output",
            str(output_dir),
            "--no-llm",
        ]
    )
    assert rc == 0
    assert (output_dir / "graph.json").is_file()
    assert (output_dir / "GRAPH_REPORT.md").is_file()


def test_analyze_cli_subcommand(fixture_site_path, capsys):
    from topo_semantic_adapter.__main__ import main

    rc = main(["analyze", str(fixture_site_path), "--format", "summary"])
    assert rc == 0
    captured = capsys.readouterr()
    assert "Graph Summary" in captured.out
