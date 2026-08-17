"""Adapter registry for dynamic parser discovery and loading."""

from __future__ import annotations

from topo_semantic_adapter.adapters.base import CommandParser, SemanticAdapter


class AdapterRegistry:
    """Holds all active command parsers and allows runtime lookup."""

    def __init__(self) -> None:
        self._parsers: list[CommandParser] = []

    def register(self, parser: CommandParser) -> None:
        """Register a single ``CommandParser``."""
        self._parsers.append(parser)

    def register_adapter(self, adapter: SemanticAdapter) -> None:
        """Register every parser exposed by a ``SemanticAdapter``."""
        for parser in adapter.supported_parsers():
            self.register(parser)

    def find_parser(self, command: str) -> CommandParser | None:
        """Return the first parser that claims it can parse ``command``."""
        for parser in self._parsers:
            if parser.can_parse(command):
                return parser
        return None

    def load_builtin(self) -> None:
        """Load all built-in adapters shipped with this package."""
        from topo_semantic_adapter.adapters.huawei import HuaweiSemanticAdapter

        self.register_adapter(HuaweiSemanticAdapter())
