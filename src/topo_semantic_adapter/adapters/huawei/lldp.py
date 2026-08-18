"""Semantic adapter for Huawei LLDP neighbor output.

Reconstructs inter-device links from the common Huawei LLDP commands:

- ``display lldp neighbor``
- ``display lldp neighbor brief``
- ``display lldp neighbor-information``
- ``display lldp neighbor-information verbose``

Each discovered neighbor produces:

- local ``device`` / ``interface`` nodes
- remote ``device`` / ``interface`` nodes
- a ``connects_to`` edge between the two interfaces
"""

from __future__ import annotations

import re

from topo_semantic_adapter.adapters.base import AdapterContext, CommandParser, ParsedEntity
from topo_semantic_adapter.models import Edge, Node

from ._helpers import (
    canonicalize_interface_name,
    device_node_id,
    device_source,
    interface_node_id,
    node_id,
)


class LldpNeighborParser(CommandParser):
    """Parse Huawei LLDP neighbor information and reconstruct physical links."""

    COMMAND_HINTS = (
        "display lldp neighbor",
        "display lldp neighbor-information",
        "display lldp nei",
    )
    SEMANTIC_CONCEPTS = ("topology", "lldp")

    @property
    def semantic_concepts(self) -> tuple[str, ...]:
        return self.SEMANTIC_CONCEPTS

    # Tokens that identify header lines so they are not parsed as data rows.
    _HEADER_TOKENS = {
        "local",
        "intf",
        "interface",
        "neighbor",
        "exptime",
        "system",
        "name",
        "port",
        "id",
        "device",
        "chassisid",
        "description",
        "hellotime",
        "age",
        "txexp",
        "rxexp",
    }

    # Classic brief table line: LocalIntf RemoteDevice RemoteIntf [Exptime]
    _BRIEF_LINE = re.compile(
        r"^\s*(?P<local_intf>\S+)\s+(?P<remote_device>\S+)\s+(?P<remote_intf>\S+)(?:\s+\S+)?$",
        re.MULTILINE,
    )

    # Table variants for ``display lldp neighbor`` without ``brief``/``verbose``.
    # Each variant has a header detector and a row regex that maps capture groups
    # to ``local_intf``, ``remote_device`` and ``remote_intf``.
    _TABLE_VARIANTS = [
        {
            "name": "brief",
            "header": re.compile(
                r"Local\s+Intf.*Neighbor\s+(?:Device\s+)?ID.*Neighbor\s+Intf",
                re.IGNORECASE,
            ),
            "row": re.compile(
                r"^\s*(?P<local_intf>\S+)\s+(?P<remote_device>\S+)\s+(?P<remote_intf>\S+)(?:\s+\S+)?$",
                re.MULTILINE,
            ),
        },
        {
            "name": "system_local_port",
            "header": re.compile(
                r"System\s+Name.*Local\s+Interface.*Port\s*ID",
                re.IGNORECASE,
            ),
            "row": re.compile(
                r"^\s*(?P<remote_device>\S+)\s+(?P<local_intf>\S+)\s+\S+\s+(?P<remote_intf>\S+)",
                re.MULTILINE,
            ),
        },
        {
            "name": "local_neighbor_intf",
            "header": re.compile(
                r"Local\s+Interface.*Neighbor\s+Interface",
                re.IGNORECASE,
            ),
            "row": re.compile(
                r"^\s*(?P<local_intf>\S+)\s+(?:\S+\s+){4}(?P<remote_intf>\S+)$",
                re.MULTILINE,
            ),
        },
    ]

    # Verbose / neighbor-information block fields.
    _VERBOSE_FIELDS = {
        "system_name": re.compile(
            r"System\s+Name\s*[:：]\s*(?P<value>\S+)", re.IGNORECASE
        ),
        "port_id": re.compile(
            r"Port\s+ID\s*[:：]\s*(?P<value>\S+)", re.IGNORECASE
        ),
        "local_intf": re.compile(
            r"(?:Local\s+Interface|Local\s+Intf)\s*[:：]\s*(?P<value>\S+)",
            re.IGNORECASE,
        ),
    }

    def can_parse(self, command: str) -> bool:
        lowered = command.strip().lower()
        return any(hint in lowered for hint in (h.lower() for h in self.COMMAND_HINTS))

    def parse(self, command: str, output: str, context: AdapterContext) -> ParsedEntity:
        entities = ParsedEntity()
        source = device_source(context)

        # Always emit the local device node so downstream has an anchor.
        local_device = device_node_id(context)
        entities.nodes.append(
            Node(
                id=local_device,
                kind="device",
                label=source,
                properties={
                    "name": source,
                    "mgmt_ip": context.device_ip,
                    "device_id": context.device_id,
                },
                source="display lldp neighbor",
            )
        )

        lowered_command = command.lower()
        explicit_brief = "brief" in lowered_command
        explicit_verbose = "verbose" in lowered_command
        explicit_neighbor_info = "neighbor-information" in lowered_command

        if explicit_verbose:
            # Verbose commands are unambiguously block-based.
            self._parse_verbose_blocks(output, entities, context, local_device)
        elif explicit_brief:
            # Brief commands use the classic table regex.
            self._parse_brief_lines(output, entities, context, local_device)
        elif explicit_neighbor_info:
            # neighbor-information is usually block-based, but fall back to tables.
            self._parse_verbose_blocks(output, entities, context, local_device)
            if not entities.edges:
                self._parse_table_variants(output, entities, context, local_device)
        else:
            # Plain ``display lldp neighbor`` has several tabular layouts.
            # Try table variants first to avoid the more permissive brief regex
            # mis-matching rows from unrelated layouts.
            self._parse_table_variants(output, entities, context, local_device)
            if not entities.edges:
                self._parse_brief_lines(output, entities, context, local_device)
            if not entities.edges:
                self._parse_verbose_blocks(output, entities, context, local_device)

        return entities

    def _parse_brief_lines(
        self,
        output: str,
        entities: ParsedEntity,
        context: AdapterContext,
        local_device: str,
    ) -> None:
        for match in self._BRIEF_LINE.finditer(output):
            local_intf = match.group("local_intf")
            remote_device = match.group("remote_device")
            remote_intf = match.group("remote_intf")
            if (
                local_intf.lower() in self._HEADER_TOKENS
                or remote_device.lower() in self._HEADER_TOKENS
                or remote_intf.lower() in self._HEADER_TOKENS
            ):
                continue
            self._add_neighbor(
                entities,
                context,
                local_device,
                local_intf,
                remote_device,
                remote_intf,
            )

    def _parse_table_variants(
        self,
        output: str,
        entities: ParsedEntity,
        context: AdapterContext,
        local_device: str,
    ) -> None:
        for variant in self._TABLE_VARIANTS:
            if not variant["header"].search(output):
                continue
            for match in variant["row"].finditer(output):
                local_intf = match.group("local_intf")
                remote_intf = match.group("remote_intf")
                remote_device = (
                    match.group("remote_device")
                    if "remote_device" in match.groupdict()
                    else ""
                )
                if (
                    local_intf.lower() in self._HEADER_TOKENS
                    or remote_intf.lower() in self._HEADER_TOKENS
                    or (remote_device and remote_device.lower() in self._HEADER_TOKENS)
                ):
                    continue
                # Some LLDP table layouts only expose local+remote interface.
                # Without a remote device name we cannot build a real neighbor
                # device node, so skip those rows.
                if not remote_device:
                    continue
                self._add_neighbor(
                    entities,
                    context,
                    local_device,
                    local_intf,
                    remote_device,
                    remote_intf,
                )
            if entities.edges:
                return

    def _parse_verbose_blocks(
        self,
        output: str,
        entities: ParsedEntity,
        context: AdapterContext,
        local_device: str,
    ) -> None:
        # Neighbor-information / verbose output is grouped by blank lines.
        for block in output.split("\n\n"):
            block = block.strip()
            if not block:
                continue
            fields: dict[str, str] = {}
            for key, pattern in self._VERBOSE_FIELDS.items():
                m = pattern.search(block)
                if m:
                    fields[key] = m.group("value")
            if "system_name" in fields and "port_id" in fields:
                local_intf = fields.get("local_intf", "")
                if not local_intf:
                    continue
                self._add_neighbor(
                    entities,
                    context,
                    local_device,
                    local_intf,
                    fields["system_name"],
                    fields["port_id"],
                )

    def _add_neighbor(
        self,
        entities: ParsedEntity,
        context: AdapterContext,
        local_device: str,
        local_intf: str,
        remote_device: str,
        remote_intf: str,
    ) -> None:
        local_source = device_source(context)
        local_intf_canon = canonicalize_interface_name(local_intf)
        remote_intf_canon = canonicalize_interface_name(remote_intf)

        local_intf_id = interface_node_id(context, local_intf_canon)
        remote_device_id = node_id(remote_device, "device", remote_device)
        remote_intf_id = node_id(remote_device, "interface", remote_intf_canon)

        entities.nodes.append(
            Node(
                id=local_intf_id,
                kind="interface",
                label=local_intf_canon,
                properties={
                    "name": local_intf_canon,
                    "device_ip": context.device_ip,
                    "device_id": context.device_id,
                },
                source="display lldp neighbor",
            )
        )
        entities.nodes.append(
            Node(
                id=remote_device_id,
                kind="device",
                label=remote_device,
                properties={"name": remote_device},
                source="display lldp neighbor",
            )
        )
        entities.nodes.append(
            Node(
                id=remote_intf_id,
                kind="interface",
                label=remote_intf_canon,
                properties={"name": remote_intf_canon, "remote_device": remote_device},
                source="display lldp neighbor",
            )
        )
        entities.edges.append(
            Edge(
                id=f"{local_intf_id}--connects-to--{remote_intf_id}",
                source=local_intf_id,
                target=remote_intf_id,
                relation="connects_to",
                properties={
                    "protocol": "lldp",
                    "local_device": local_source,
                    "remote_device": remote_device,
                },
                provenance="display lldp neighbor",
            )
        )
