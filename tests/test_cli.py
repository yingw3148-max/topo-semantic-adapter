"""Tests for the command-line entry point."""

from __future__ import annotations

import pytest

pytest.importorskip("toposphere_core")

from topo_semantic_adapter.__main__ import main
from tests.fixtures import write_fixture_site


def test_cli_report_output(tmp_path, capsys):
    site_dir = write_fixture_site(tmp_path)
    rc = main([str(site_dir)])
    assert rc == 0

    captured = capsys.readouterr()
    assert "拓扑分析报告" in captured.out
    assert "节点数: 9" in captured.out


def test_cli_summary_format(tmp_path, capsys):
    site_dir = write_fixture_site(tmp_path)
    rc = main([str(site_dir), "--format", "summary"])
    assert rc == 0
    assert "Graph Summary" in capsys.readouterr().out


def test_cli_intent_filter(tmp_path, capsys):
    site_dir = write_fixture_site(tmp_path)
    rc = main([str(site_dir), "--intent", "impact_analysis", "--format", "summary"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "Nodes:" in out


def test_cli_missing_site_dir(capsys):
    rc = main(["/nonexistent/path"])
    assert rc == 1
    assert "does not exist" in capsys.readouterr().err
