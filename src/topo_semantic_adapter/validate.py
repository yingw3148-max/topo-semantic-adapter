"""Validation helpers for parser output.

Inspired by graphify's validate.py: every extraction should be schema-checked
before it is merged into the graph. Errors are returned as a list of strings so
callers can decide whether to raise, warn, or drop the invalid data.
"""

from __future__ import annotations

from topo_semantic_adapter.adapters.base import ParsedEntity

VALID_CONFIDENCE = {"EXTRACTED", "INFERRED", "AMBIGUOUS"}


def validate_parsed_entity(entities: ParsedEntity) -> list[str]:
    """Validate a ``ParsedEntity`` and return a list of human-readable errors."""
    errors: list[str] = []
    node_ids = set()

    for index, node in enumerate(entities.nodes):
        prefix = f"node[{index}]"
        if not node.id:
            errors.append(f"{prefix}: missing id")
        if not node.kind:
            errors.append(f"{prefix} ({node.id!r}): missing kind")
        if node.id in node_ids:
            errors.append(f"{prefix}: duplicate node id {node.id!r}")
        node_ids.add(node.id)

    edge_node_ids = {node.id for node in entities.nodes}
    edge_ids = set()

    for index, edge in enumerate(entities.edges):
        prefix = f"edge[{index}]"
        if not edge.id:
            errors.append(f"{prefix}: missing id")
        if not edge.source:
            errors.append(f"{prefix} ({edge.id!r}): missing source")
        if not edge.target:
            errors.append(f"{prefix} ({edge.id!r}): missing target")
        if not edge.relation:
            errors.append(f"{prefix} ({edge.id!r}): missing relation")
        if edge.source and edge.target and edge.source not in edge_node_ids:
            errors.append(
                f"{prefix}: source {edge.source!r} is not defined by any node"
            )
        if edge.target and edge.target not in edge_node_ids:
            errors.append(
                f"{prefix}: target {edge.target!r} is not defined by any node"
            )
        if edge.id in edge_ids:
            errors.append(f"{prefix}: duplicate edge id {edge.id!r}")
        edge_ids.add(edge.id)
        if edge.confidence not in VALID_CONFIDENCE:
            errors.append(
                f"{prefix}: invalid confidence {edge.confidence!r}, "
                f"must be one of {VALID_CONFIDENCE}"
            )

    return errors


def assert_valid(entities: ParsedEntity) -> None:
    """Raise ``ValueError`` if the parsed entity contains validation errors."""
    errors = validate_parsed_entity(entities)
    if errors:
        raise ValueError("Invalid ParsedEntity:\n" + "\n".join(f"  - {e}" for e in errors))
