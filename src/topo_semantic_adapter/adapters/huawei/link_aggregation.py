"""Semantic adapter for Huawei ``display link-aggregation verbose`` output."""

from __future__ import annotations

import re

from topo_semantic_adapter.adapters.base import AdapterContext, CommandParser, ParsedEntity
from topo_semantic_adapter.models import Edge, Node

from ._helpers import canonicalize_interface_name, interface_node_id, node_id


class LinkAggregationParser(CommandParser):
    """Extract link aggregation groups and their member ports.

    Output entities:

    - ``Node(kind="link_aggregation_group")`` for each ``Eth-TrunkX``.
    - ``Node(kind="interface")`` for each member port.
    - ``Edge(relation="member_of")`` connecting a member port to its group,
      with ``selected_status`` property (Selected / Unselected / Individual).
    """

    COMMAND_HINTS = ("display link-aggregation verbose",)
    SEMANTIC_CONCEPTS = ("link_aggregation", "lag_member_state")

    @property
    def semantic_concepts(self) -> tuple[str, ...]:
        return self.SEMANTIC_CONCEPTS

    _INTERFACE_SPLIT = re.compile(r"(?=Interface\s+\S+)")
    _INTERFACE_NAME = re.compile(r"Interface\s+(?P<group>\S+)")
    _MEMBER_LINE = re.compile(
        r"^(?P<port>\S+)\s+(?P<status>S|U|I|Selected|Unselected|Individual)\b",
        re.MULTILINE,
    )

    def can_parse(self, command: str) -> bool:
        lowered = command.strip().lower()
        return any(hint in lowered for hint in (h.lower() for h in self.COMMAND_HINTS))

    def parse(self, command: str, output: str, context: AdapterContext) -> ParsedEntity:
        entities = ParsedEntity()
        blocks = self._INTERFACE_SPLIT.split(output)

        for block in blocks:
            match = self._INTERFACE_NAME.search(block)
            if not match:
                continue

            group_name = match.group("group")
            group_id = node_id(
                context.device_id or context.device_ip,
                "link_aggregation_group",
                group_name,
            )
            entities.nodes.append(
                Node(
                    id=group_id,
                    kind="link_aggregation_group",
                    label=group_name,
                    properties={
                        "name": group_name,
                        "device_ip": context.device_ip,
                        "device_id": context.device_id,
                    },
                    source="display link-aggregation verbose",
                )
            )

            for port_name, status in self._iter_members(block):
                port_id = interface_node_id(context, port_name)
                entities.nodes.append(
                    Node(
                        id=port_id,
                        kind="interface",
                        label=canonicalize_interface_name(port_name),
                        properties={
                            "name": canonicalize_interface_name(port_name),
                            "device_ip": context.device_ip,
                            "device_id": context.device_id,
                            "lag_member_state": status,
                        },
                        source="display link-aggregation verbose",
                    )
                )
                entities.edges.append(
                    Edge(
                        id=f"{port_id}--member-of--{group_id}",
                        source=port_id,
                        target=group_id,
                        relation="member_of",
                        properties={"selected_status": status},
                        provenance="display link-aggregation verbose",
                    )
                )

        return entities

    def _iter_members(self, block: str):
        for match in self._MEMBER_LINE.finditer(block):
            yield match.group("port"), self._normalize_status(match.group("status"))

    @staticmethod
    def _normalize_status(token: str) -> str:
        return {
            "s": "Selected",
            "u": "Unselected",
            "i": "Individual",
            "selected": "Selected",
            "unselected": "Unselected",
            "individual": "Individual",
        }.get(token.lower(), token)
