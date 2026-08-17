"""Tests for the adapter registry."""

from __future__ import annotations

from topo_semantic_adapter.adapters.base import (
    AdapterContext,
    CommandParser,
    ParsedEntity,
)
from topo_semantic_adapter.adapters.huawei import HuaweiSemanticAdapter
from topo_semantic_adapter.adapters.huawei.lldp import LldpNeighborParser
from topo_semantic_adapter.registry import AdapterRegistry


class DummyParser(CommandParser):
    """A parser that only claims a single command."""

    def can_parse(self, command: str) -> bool:
        return command == "display dummy"

    def parse(self, command: str, output: str, context: AdapterContext) -> ParsedEntity:
        return ParsedEntity()


def test_register_and_find_parser():
    registry = AdapterRegistry()
    parser = DummyParser()
    registry.register(parser)

    assert registry.find_parser("display dummy") is parser
    assert registry.find_parser("display other") is None


def test_register_adapter():
    registry = AdapterRegistry()
    registry.register_adapter(HuaweiSemanticAdapter())

    assert registry.find_parser("display lldp neighbor brief") is not None
    assert isinstance(registry.find_parser("display lldp neighbor brief"), LldpNeighborParser)


def test_load_builtin_includes_huawei_parsers():
    registry = AdapterRegistry()
    registry.load_builtin()

    assert registry.find_parser("display lldp neighbor brief") is not None
    assert registry.find_parser("display ospf peer") is not None
    assert registry.find_parser("display vrrp") is not None
    assert registry.find_parser("display dhcp snooping binding") is not None
    assert registry.find_parser("display link-aggregation verbose") is not None


def test_find_parser_returns_first_match():
    registry = AdapterRegistry()
    first = DummyParser()
    second = DummyParser()
    registry.register(first)
    registry.register(second)

    assert registry.find_parser("display dummy") is first
