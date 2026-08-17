"""Shared pytest fixtures for the adapter test suite."""

from __future__ import annotations

from pathlib import Path

import pytest

from topo_semantic_adapter.adapters.base import AdapterContext
from topo_semantic_adapter.registry import AdapterRegistry


@pytest.fixture
def fixture_site_path() -> Path:
    """Return the path to the fixture site directory."""
    return Path(__file__).parent / "fixtures" / "湖北大学配置"


@pytest.fixture
def sample_context() -> AdapterContext:
    """Return a typical adapter context for unit tests."""
    return AdapterContext(
        device_ip="10.0.0.1",
        device_id="core-sw-01",
        site="湖北大学",
    )


@pytest.fixture
def builtin_registry() -> AdapterRegistry:
    """Return an adapter registry with all built-in parsers loaded."""
    registry = AdapterRegistry()
    registry.load_builtin()
    return registry
