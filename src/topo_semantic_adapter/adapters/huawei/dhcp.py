"""Semantic adapter for Huawei DHCP Snooping binding output."""

from __future__ import annotations

import re

from topo_semantic_adapter.adapters.base import AdapterContext, CommandParser, ParsedEntity
from topo_semantic_adapter.models import Node

from ._helpers import canonicalize_interface_name, interface_node_id


class DhcpSnoopingParser(CommandParser):
    """Extract DHCP snooping bindings and attach lease state to interfaces."""

    COMMAND_HINTS = ("display dhcp snooping binding",)
    SEMANTIC_CONCEPTS = ("dhcp", "dhcp_lease_state")

    @property
    def semantic_concepts(self) -> tuple[str, ...]:
        return self.SEMANTIC_CONCEPTS

    # Matches data lines like:
    # 0001-0203-0405  10.1.1.10       86300   dhcp-snooping  10   GE0/0/1
    _DATA_LINE = re.compile(
        r"^(?P<mac>[\da-fA-F\-:.]+)\s+"
        r"(?P<ip>\S+)\s+"
        r"(?P<lease>\d+)\s+"
        r"(?P<type>\S+)\s+"
        r"(?P<vlan>\S+)\s+"
        r"(?P<interface>\S+)",
        re.MULTILINE,
    )

    def can_parse(self, command: str) -> bool:
        lowered = command.strip().lower()
        return any(hint in lowered for hint in (h.lower() for h in self.COMMAND_HINTS))

    def parse(self, command: str, output: str, context: AdapterContext) -> ParsedEntity:
        entities = ParsedEntity()

        for match in self._DATA_LINE.finditer(output):
            interface = canonicalize_interface_name(match.group("interface"))
            intf_id = interface_node_id(context, interface)
            entities.nodes.append(
                Node(
                    id=intf_id,
                    kind="interface",
                    label=interface,
                    properties={
                        "name": interface,
                        "device_ip": context.device_ip,
                        "device_id": context.device_id,
                        "dhcp_lease_state": "bound",
                        "dhcp_bound_ip": match.group("ip"),
                        "dhcp_bound_mac": match.group("mac"),
                        "dhcp_lease_time": int(match.group("lease")),
                        "dhcp_vlan": match.group("vlan"),
                    },
                    source="display dhcp snooping binding",
                )
            )

        return entities
