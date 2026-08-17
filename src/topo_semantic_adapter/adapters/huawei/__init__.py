"""Huawei CLI semantic adapter."""

from __future__ import annotations

from typing import Iterable

from topo_semantic_adapter.adapters.base import CommandParser, SemanticAdapter

from .dhcp import DhcpSnoopingParser
from .link_aggregation import LinkAggregationParser
from .lldp import LldpNeighborParser
from .ospf import OspfNeighborParser
from .vrrp import VrrpParser


class HuaweiSemanticAdapter(SemanticAdapter):
    @property
    def name(self) -> str:
        return "huawei-cli"

    @property
    def vendor(self) -> str:
        return "huawei"

    def supported_parsers(self) -> Iterable[CommandParser]:
        return [
            LldpNeighborParser(),
            OspfNeighborParser(),
            VrrpParser(),
            DhcpSnoopingParser(),
            LinkAggregationParser(),
        ]
