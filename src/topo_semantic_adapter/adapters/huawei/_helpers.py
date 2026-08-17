"""Shared helpers for Huawei CLI parsers."""

from __future__ import annotations

from topo_semantic_adapter.adapters.base import AdapterContext

_INTERFACE_ABBREVIATIONS = {
    "GE": "GigabitEthernet",
    "XG": "XGigabitEthernet",
}


def device_source(context: AdapterContext) -> str:
    """Return the canonical source token for a device.

    Prefer ``device_id`` (hostname) over ``device_ip`` so that LLDP-discovered
    remote devices and locally processed devices share the same namespace when
    they report the same system name.
    """
    return context.device_id or context.device_ip


def canonicalize_interface_name(name: str) -> str:
    """Normalize common Huawei interface abbreviations.

    Examples: ``GE0/0/1`` → ``GigabitEthernet0/0/1``.
    """
    name = name.strip()
    if len(name) < 3:
        return name
    prefix = name[:2].upper()
    rest = name[2:]
    if prefix in _INTERFACE_ABBREVIATIONS:
        if rest and (rest[0].isdigit() or rest[0] == "/"):
            return _INTERFACE_ABBREVIATIONS[prefix] + rest
    return name


def node_id(source: str, kind: str, identifier: str) -> str:
    """Build a TopoSphere Core style deterministic node ID."""
    return f"{source}:{kind}:{identifier}"


def interface_node_id(context: AdapterContext, local_name: str) -> str:
    """Build a deterministic interface node ID from the current context."""
    return node_id(
        device_source(context), "interface", canonicalize_interface_name(local_name)
    )


def device_node_id(context: AdapterContext) -> str:
    """Build a deterministic device node ID from the current context."""
    src = device_source(context)
    return node_id(src, "device", src)
