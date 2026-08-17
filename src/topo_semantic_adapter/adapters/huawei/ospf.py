"""Semantic adapter for Huawei OSPF neighbor output."""

from __future__ import annotations

import re

from topo_semantic_adapter.adapters.base import AdapterContext, CommandParser, ParsedEntity
from topo_semantic_adapter.models import Node

from ._helpers import canonicalize_interface_name, interface_node_id


class OspfNeighborParser(CommandParser):
    """Extract OSPF neighbor state and attach it to the local interface node."""

    COMMAND_HINTS = ("display ospf peer",)
    SEMANTIC_CONCEPTS = ("ospf", "ospf_neighbor_state")

    @property
    def semantic_concepts(self) -> tuple[str, ...]:
        return self.SEMANTIC_CONCEPTS

    # Matches: "Area 0.0.0.0 interface 10.1.1.1(GigabitEthernet0/0/1)'s neighbors"
    _INTERFACE_BLOCK = re.compile(
        r"interface\s+(?P<local_ip>\S+)\((?P<local_intf>[^)]+)\)'s\s+neighbors",
        re.IGNORECASE,
    )
    _ROUTER_ID = re.compile(r"Router\s+ID\s*[:：]\s*(?P<value>\S+)")
    _STATE = re.compile(r"State\s*[:：]\s*(?P<value>\S+)", re.IGNORECASE)

    def can_parse(self, command: str) -> bool:
        lowered = command.strip().lower()
        return any(hint in lowered for hint in (h.lower() for h in self.COMMAND_HINTS))

    def parse(self, command: str, output: str, context: AdapterContext) -> ParsedEntity:
        entities = ParsedEntity()

        for match in self._INTERFACE_BLOCK.finditer(output):
            local_intf = canonicalize_interface_name(match.group("local_intf"))
            start = match.end()
            next_match = self._INTERFACE_BLOCK.search(output, start)
            end = next_match.start() if next_match else len(output)
            segment = output[start:end]

            router_id = ""
            state = ""

            m = self._ROUTER_ID.search(segment)
            if m:
                router_id = m.group("value")
            m = self._STATE.search(segment)
            if m:
                state = m.group("value")

            intf_id = interface_node_id(context, local_intf)
            entities.nodes.append(
                Node(
                    id=intf_id,
                    kind="interface",
                    label=local_intf,
                    properties={
                        "name": local_intf,
                        "device_ip": context.device_ip,
                        "device_id": context.device_id,
                        "ospf_neighbor_state": state,
                        "ospf_neighbor_router_id": router_id,
                    },
                    source="display ospf peer",
                )
            )

        return entities
