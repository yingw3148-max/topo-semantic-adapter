"""Tests for Huawei adapter shared helpers."""

from __future__ import annotations

from topo_semantic_adapter.adapters.base import AdapterContext
from topo_semantic_adapter.adapters.huawei import HuaweiSemanticAdapter
from topo_semantic_adapter.adapters.huawei._helpers import (
    canonicalize_interface_name,
    device_node_id,
    device_source,
    interface_node_id,
    node_id,
)


def test_device_source_prefers_device_id():
    context = AdapterContext(device_ip="10.0.0.1", device_id="core-sw-01", site="site-a")
    assert device_source(context) == "core-sw-01"


def test_device_source_falls_back_to_ip():
    context = AdapterContext(device_ip="10.0.0.1", device_id="", site="site-a")
    assert device_source(context) == "10.0.0.1"


def test_canonicalize_interface_name_abbreviations():
    assert canonicalize_interface_name("GE0/0/1") == "GigabitEthernet0/0/1"
    assert canonicalize_interface_name("XG0/0/3") == "XGigabitEthernet0/0/3"
    assert canonicalize_interface_name("GigabitEthernet0/0/1") == "GigabitEthernet0/0/1"


def test_canonicalize_interface_name_short_input():
    assert canonicalize_interface_name("E") == "E"
    assert canonicalize_interface_name("") == ""


def test_node_id_format():
    assert node_id("core-sw-01", "interface", "GE0/0/1") == "core-sw-01:interface:GE0/0/1"


def test_interface_node_id_uses_canonical_name():
    context = AdapterContext(device_ip="10.0.0.1", device_id="sw1", site="site-a")
    assert interface_node_id(context, "GE0/0/1") == "sw1:interface:GigabitEthernet0/0/1"


def test_device_node_id():
    context = AdapterContext(device_ip="10.0.0.1", device_id="sw1", site="site-a")
    assert device_node_id(context) == "sw1:device:sw1"


def test_huawei_adapter_metadata():
    adapter = HuaweiSemanticAdapter()
    assert adapter.name == "huawei-cli"
    assert adapter.vendor == "huawei"
    assert len(list(adapter.supported_parsers())) == 5
