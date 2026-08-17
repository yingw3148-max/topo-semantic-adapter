"""Tests for the core adapter abstractions."""

from __future__ import annotations

from topo_semantic_adapter.adapters.base import (
    AdapterContext,
    CommandParser,
    ParsedEntity,
)
from topo_semantic_adapter.models import Edge, Node


class MinimalParser(CommandParser):
    def can_parse(self, command: str) -> bool:
        return command == "display minimal"

    def parse(self, command: str, output: str, context: AdapterContext) -> ParsedEntity:
        return ParsedEntity()


def test_parsed_entity_to_graph():
    entity = ParsedEntity(
        nodes=[Node(id="a", kind="device")],
        edges=[Edge(id="e1", source="a", target="b", relation="connects_to")],
    )
    graph = entity.to_graph()
    assert "a" in graph.nodes
    assert "e1" in graph.edges


def test_command_parser_default_concepts():
    parser = MinimalParser()
    assert parser.semantic_concepts == ()
