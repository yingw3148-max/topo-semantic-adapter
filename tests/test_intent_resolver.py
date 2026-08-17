"""Tests for the intent resolver."""

from __future__ import annotations

from topo_semantic_adapter.intent_resolver import IntentResolver


def test_fault_root_cause_intent():
    profile = IntentResolver().resolve("fault_root_cause")
    assert profile.intent == "fault_root_cause"
    assert "dhcp_lease_state" in profile.required_attributes
    assert "ospf_neighbor_state" in profile.required_attributes
    assert "topology" in profile.adapter_hints


def test_impact_analysis_intent():
    profile = IntentResolver().resolve("impact_analysis")
    assert profile.intent == "impact_analysis"
    assert "lag_member_state" in profile.required_attributes
    assert "vrrp_role_state" in profile.required_attributes
    assert "topology" in profile.adapter_hints


def test_unknown_intent_returns_empty_profile():
    profile = IntentResolver().resolve("unknown_intent")
    assert profile.intent == "unknown_intent"
    assert profile.required_attributes == ()
