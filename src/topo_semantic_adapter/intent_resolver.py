"""Map downstream task intents to the attribute sets they need."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class IntentProfile:
    """The attribute requirements for a given downstream intent."""

    intent: str
    required_attributes: tuple[str, ...]
    optional_attributes: tuple[str, ...] = ()
    adapter_hints: tuple[str, ...] = ()


_INTENT_MAP: dict[str, IntentProfile] = {
    "fault_root_cause": IntentProfile(
        intent="fault_root_cause",
        required_attributes=("dhcp_lease_state", "ospf_neighbor_state"),
        # topology is always included so the base LLDP graph is rebuilt.
        adapter_hints=("topology", "dhcp", "ospf"),
    ),
    "impact_analysis": IntentProfile(
        intent="impact_analysis",
        required_attributes=("lag_member_state", "vrrp_role_state"),
        adapter_hints=("topology", "link_aggregation", "vrrp"),
    ),
}


class IntentResolver:
    """Resolve an intent string into an ``IntentProfile``."""

    def resolve(self, intent: str) -> IntentProfile:
        return _INTENT_MAP.get(
            intent,
            IntentProfile(intent=intent, required_attributes=()),
        )
