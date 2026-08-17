"""Shared pytest fixtures for the adapter test suite."""

from __future__ import annotations

from pathlib import Path

import pytest

from topo_semantic_adapter.adapters.base import AdapterContext
from topo_semantic_adapter.registry import AdapterRegistry
from tests.fixtures import write_fixture_site


@pytest.fixture(scope="session")
def fixture_site_path(tmp_path_factory) -> Path:
    """Return a generated copy of the sample production site directory.

    The content is identical to the static files under ``tests/fixtures/湖北大学配置``,
    but generating it at runtime guarantees tests pass even when only the tracked
    source files are copied.
    """
    site_root = tmp_path_factory.mktemp("fixture-site")
    return write_fixture_site(site_root)


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
