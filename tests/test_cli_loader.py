"""Tests for the CLI file loader."""

from __future__ import annotations

import tempfile
from pathlib import Path

from topo_semantic_adapter.cli_loader import CLIFileLoader, DEFAULT_DELIMITER


SAMPLE = f"""display version
VRP (R) software, Version 8.200
Copyright (C) 2012-2024 Huawei Technologies Co., Ltd.
{DEFAULT_DELIMITER}
display link-aggregation verbose
Load-balance Type: Shar -- Load-balance, and NonS -- Non-Load-balance
Port Status: S -- Selected, U -- Unselected, I -- Individual
Local:
Totalnumberof trunk members: 2
Number of active members: 2
Interface Eth-Trunk1
PortName                      Status      Weight
GigabitEthernet0/0/1          Selected    1
GigabitEthernet0/0/2          Unselected  1
"""


def test_cli_loader_splits_blocks():
    with tempfile.TemporaryDirectory() as tmp:
        site_name = "site-a"
        device_dir = Path(tmp) / f"{site_name}-配置" / "inspect" / "10.0.0.1_sw1"
        device_dir.mkdir(parents=True)
        result_file = device_dir / "CommonCollectResult"
        result_file.write_text(SAMPLE, encoding="utf-8")

        loader = CLIFileLoader(site_name, tmp)
        blocks = list(loader.iter_blocks())

        assert len(blocks) == 2
        first, second = blocks

        assert first.command == "display version"
        assert "VRP (R) software" in first.output
        assert first.device_ip == "10.0.0.1"
        assert first.device_id == "sw1"

        assert second.command == "display link-aggregation verbose"
        assert "Eth-Trunk1" in second.output


def test_cli_loader_handles_missing_inspect_dir():
    with tempfile.TemporaryDirectory() as tmp:
        loader = CLIFileLoader(site_name="missing", base_path=tmp)
        assert list(loader.iter_blocks()) == []


def test_cli_loader_skips_device_dir_without_result_file():
    with tempfile.TemporaryDirectory() as tmp:
        site_name = "site-a"
        device_dir = Path(tmp) / f"{site_name}-配置" / "inspect" / "10.0.0.1_sw1"
        device_dir.mkdir(parents=True)

        loader = CLIFileLoader(site_name, tmp)
        assert list(loader.iter_blocks()) == []


def test_cli_loader_parses_dir_without_underscore():
    with tempfile.TemporaryDirectory() as tmp:
        site_name = "site-a"
        device_dir = Path(tmp) / f"{site_name}-配置" / "inspect" / "my-device"
        device_dir.mkdir(parents=True)
        (device_dir / "CommonCollectResult").write_text(
            "display version\nVRP", encoding="utf-8"
        )

        loader = CLIFileLoader(site_name, tmp)
        blocks = list(loader.iter_blocks())
        assert len(blocks) == 1
        assert blocks[0].device_ip == "my-device"
        assert blocks[0].device_id == ""


def test_cli_loader_ignores_empty_blocks():
    with tempfile.TemporaryDirectory() as tmp:
        site_name = "site-a"
        device_dir = Path(tmp) / f"{site_name}-配置" / "inspect" / "10.0.0.1_sw1"
        device_dir.mkdir(parents=True)
        (device_dir / "CommonCollectResult").write_text(
            f"{DEFAULT_DELIMITER}\n\ndisplay version\nVRP\n{DEFAULT_DELIMITER}",
            encoding="utf-8",
        )

        loader = CLIFileLoader(site_name, tmp)
        blocks = list(loader.iter_blocks())
        assert len(blocks) == 1
        assert blocks[0].command == "display version"


def test_cli_loader_skips_non_file_common_collect_result():
    with tempfile.TemporaryDirectory() as tmp:
        site_name = "site-a"
        device_dir = Path(tmp) / f"{site_name}-配置" / "inspect" / "10.0.0.1_sw1"
        device_dir.mkdir(parents=True)
        (device_dir / "CommonCollectResult").mkdir()

        loader = CLIFileLoader(site_name, tmp)
        assert list(loader.iter_blocks()) == []


def test_cli_loader_skips_files_in_inspect_dir():
    with tempfile.TemporaryDirectory() as tmp:
        site_name = "site-a"
        inspect = Path(tmp) / f"{site_name}-配置" / "inspect"
        inspect.mkdir(parents=True)
        (inspect / "not-a-directory").write_text("ignored", encoding="utf-8")

        loader = CLIFileLoader(site_name, tmp)
        assert list(loader.iter_blocks()) == []
