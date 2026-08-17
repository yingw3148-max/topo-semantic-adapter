"""Build a ``toposphere_core.TopoGraph`` from parsed CLI blocks."""

from __future__ import annotations

from dataclasses import replace

from toposphere_core import TopoGraph

from topo_semantic_adapter.adapters.base import AdapterContext
from topo_semantic_adapter.cli_loader import CommandBlock
from topo_semantic_adapter.intent_resolver import IntentResolver
from topo_semantic_adapter.registry import AdapterRegistry
from topo_semantic_adapter.toposphere_bridge import convert_edge, convert_node


class GraphBuilder:
    """Consume ``CommandBlock``s, run matching parsers, and populate a ``TopoGraph``.

    This is the primary output boundary of the adapter layer. Callers receive a
    persistent ``toposphere_core.TopoGraph`` that can be materialized into a
    ``GraphView`` for downstream analysis.
    """

    def __init__(
        self,
        registry: AdapterRegistry | None = None,
        intent: str | None = None,
        *,
        target: TopoGraph | None = None,
        db_path: str = ":memory:",
    ):
        self.registry = registry or AdapterRegistry()
        self.intent_profile = IntentResolver().resolve(intent) if intent else None
        self._topograph = target if target is not None else TopoGraph(db_path)

    def consume(self, block: CommandBlock) -> None:
        """Parse a single command block and upsert the resulting entities."""
        parser = self.registry.find_parser(block.command)
        if parser is None:
            return

        if self.intent_profile is not None:
            hints = self.intent_profile.adapter_hints
            if hints and not any(h in parser.semantic_concepts for h in hints):
                return

        context = AdapterContext(
            device_ip=block.device_ip,
            device_id=block.device_id,
            site=block.site,
            intent=self.intent_profile.intent if self.intent_profile else None,
        )
        entities = parser.parse(block.command, block.output, context)
        producer = parser.__class__.__name__

        for node in entities.nodes:
            topo_node = convert_node(
                node, source_file=block.source_file, producer=producer
            )
            existing = self._topograph.get_node(topo_node.id)
            if existing is not None:
                merged_metadata = dict(existing.metadata)
                merged_metadata.update(topo_node.metadata)
                topo_node = replace(
                    topo_node,
                    metadata=merged_metadata,
                    provenance=existing.provenance + topo_node.provenance,
                )
            self._topograph.add_node(topo_node)

        for edge in entities.edges:
            self._topograph.add_edge(
                convert_edge(edge, source_file=block.source_file, producer=producer)
            )

    def consume_many(self, blocks: list[CommandBlock]) -> None:
        for block in blocks:
            self.consume(block)

    def build(self) -> TopoGraph:
        """Return the populated ``TopoGraph``."""
        return self._topograph
