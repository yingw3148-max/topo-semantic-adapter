"""Semantic adapter for Huawei VRRP output."""

from __future__ import annotations

import re

from topo_semantic_adapter.adapters.base import AdapterContext, CommandParser, ParsedEntity
from topo_semantic_adapter.models import Node

from ._helpers import canonicalize_interface_name, interface_node_id


class VrrpParser(CommandParser):
    """Extract VRRP role/state and attach it to the local interface node."""

    COMMAND_HINTS = ("display vrrp",)
    SEMANTIC_CONCEPTS = ("vrrp", "vrrp_role_state")

    @property
    def semantic_concepts(self) -> tuple[str, ...]:
        return self.SEMANTIC_CONCEPTS

    # Matches: "GigabitEthernet0/0/1 | Virtual Router 1"
    _BLOCK = re.compile(
        r"^(?P<interface>\S+)\s*\|\s*Virtual\s+Router\s+(?P<vrid>\d+)",
        re.MULTILINE,
    )
    _STATE = re.compile(r"State\s*[:：]\s*(?P<value>\S+)", re.IGNORECASE)
    _VIRTUAL_IP = re.compile(r"Virtual\s+IP\s*[:：]\s*(?P<value>\S+)", re.IGNORECASE)

    def can_parse(self, command: str) -> bool:
        lowered = command.strip().lower()
        return any(hint in lowered for hint in (h.lower() for h in self.COMMAND_HINTS))

    def parse(self, command: str, output: str, context: AdapterContext) -> ParsedEntity:
        entities = ParsedEntity()

        for match in self._BLOCK.finditer(output):
            interface = canonicalize_interface_name(match.group("interface"))
            vrid = match.group("vrid")
            start = match.end()
            next_match = self._BLOCK.search(output, start)
            end = next_match.start() if next_match else len(output)
            segment = output[start:end]

            state = ""
            virtual_ip = ""

            m = self._STATE.search(segment)
            if m:
                state = m.group("value")
            m = self._VIRTUAL_IP.search(segment)
            if m:
                virtual_ip = m.group("value")

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
                        "vrrp_role_state": state,
                        "vrrp_vrid": vrid,
                        "vrrp_virtual_ip": virtual_ip,
                    },
                    source="display vrrp",
                )
            )

        return entities
