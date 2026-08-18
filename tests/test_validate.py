"""Tests for parser-output validation."""

from __future__ import annotations

import pytest

from topo_semantic_adapter.adapters.base import ParsedEntity
from topo_semantic_adapter.models import Edge, Node
from topo_semantic_adapter.validate import assert_valid, validate_parsed_entity


def test_valid_entity_has_no_errors():
    entity = ParsedEntity(
        nodes=[Node(id="a", kind="device"), Node(id="b", kind="device")],
        edges=[Edge(id="e1", source="a", target="b", relation="connects_to")],
    )
    assert validate_parsed_entity(entity) == []


def test_duplicate_node_id():
    entity = ParsedEntity(
        nodes=[Node(id="a", kind="device"), Node(id="a", kind="interface")]
    )
    errors = validate_parsed_entity(entity)
    assert any("duplicate node id" in e for e in errors)


def test_missing_node_kind():
    entity = ParsedEntity(nodes=[Node(id="a", kind="")])
    errors = validate_parsed_entity(entity)
    assert any("missing kind" in e for e in errors)


def test_edge_with_undefined_source():
    entity = ParsedEntity(
        nodes=[Node(id="a", kind="device")],
        edges=[Edge(id="e1", source="a", target="missing", relation="connects_to")],
    )
    errors = validate_parsed_entity(entity)
    assert any("target" in e and "not defined" in e for e in errors)


def test_invalid_confidence():
    entity = ParsedEntity(
        nodes=[Node(id="a", kind="device"), Node(id="b", kind="device")],
        edges=[
            Edge(
                id="e1",
                source="a",
                target="b",
                relation="connects_to",
                confidence="GUESS",
            )
        ],
    )
    errors = validate_parsed_entity(entity)
    assert any("invalid confidence" in e for e in errors)


def test_assert_valid_raises():
    entity = ParsedEntity(nodes=[Node(id="a", kind="")])
    with pytest.raises(ValueError):
        assert_valid(entity)
