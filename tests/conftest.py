"""Shared pytest fixtures for the adapter test suite."""

from __future__ import annotations

from pathlib import Path

import pytest

from topo_semantic_adapter.adapters.base import AdapterContext
from topo_semantic_adapter.registry import AdapterRegistry


@pytest.fixture(scope="session")
def fixture_site_path() -> Path:
    """Return the static sample production site directory.

    Tests operate directly on the files under ``tests/fixtures/湖北大学配置`` so that
    local production sample data can be swapped in without changing test code.
    """
    site_dir = Path(__file__).resolve().parent / "fixtures" / "湖北大学配置"
    if not site_dir.is_dir():
        pytest.skip(f"Sample fixture site not found: {site_dir}")
    return site_dir


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
