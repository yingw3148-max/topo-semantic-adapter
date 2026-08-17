"""Fixture factory for integration tests.

The static files under ``湖北大学配置/`` mirror real production data. This module
provides the same content programmatically so tests stay self-contained even when
the static files are not present (e.g. after copying only tracked source files).
"""

from __future__ import annotations

from pathlib import Path

from topo_semantic_adapter.cli_loader import DEFAULT_DELIMITER

_DELIM = DEFAULT_DELIMITER

_CORE_SW01 = f"""display lldp neighbor brief
Local Intf        Neighbor Device ID        Neighbor Intf        Exptime
GE0/0/1           edge-sw-02                GE0/0/1              120
{_DELIM}
display link-aggregation verbose
Load-balance Type: Shar -- Load-balance, and NonS -- Non-Load-balance
Port Status: S -- Selected, U -- Unselected, I -- Individual
Local:
Interface Eth-Trunk1
PortName                      Status      Weight
GigabitEthernet0/0/2          Selected    1
GigabitEthernet0/0/3          Unselected  1
{_DELIM}
display ospf peer
OSPF Process 1 with Router ID 1.1.1.1
 Area 0.0.0.0 interface 10.1.1.1(GigabitEthernet0/0/1)'s neighbors
 Router ID: 2.2.2.2          Address: 10.1.1.2
   State: Full           Mode:Nbr is Master           Priority: 1
{_DELIM}
display vrrp
GigabitEthernet0/0/1 | Virtual Router 1
    State: Master
    Virtual IP: 10.1.1.254
{_DELIM}
display dhcp snooping binding
DHCP Snooping Bindings:
MAC Address     IP Address      Lease Time(seconds) Type       VLAN Interface
0001-0203-0405  10.1.1.10       86300               dhcp-snooping 10   GE0/0/2
"""

_EDGE_SW02 = f"""display lldp neighbor brief
Local Intf        Neighbor Device ID        Neighbor Intf        Exptime
GE0/0/1           core-sw-01                GE0/0/1              120
{_DELIM}
display link-aggregation verbose
Load-balance Type: Shar -- Load-balance, and NonS -- Non-Load-balance
Port Status: S -- Selected, U -- Unselected, I -- Individual
Local:
Interface Eth-Trunk1
PortName                      Status      Weight
GigabitEthernet0/0/2          Selected    1
{_DELIM}
display vrrp
GigabitEthernet0/0/1 | Virtual Router 1
    State: Backup
    Virtual IP: 10.1.1.254
{_DELIM}
display dhcp snooping binding
DHCP Snooping Bindings:
MAC Address     IP Address      Lease Time(seconds) Type       VLAN Interface
0001-0203-0406  10.1.2.11       86000               dhcp-snooping 20   GE0/0/1
"""


def write_fixture_site(site_root: Path) -> Path:
    """Write the two-device sample site to ``site_root/湖北大学配置``."""
    site_dir = site_root / "湖北大学配置"
    inspect = site_dir / "inspect"

    core_dir = inspect / "10.185.0.1_core-sw-01"
    core_dir.mkdir(parents=True, exist_ok=True)
    (core_dir / "CommonCollectResult").write_text(_CORE_SW01, encoding="utf-8")

    edge_dir = inspect / "172.16.1.9_edge-sw-02"
    edge_dir.mkdir(parents=True, exist_ok=True)
    (edge_dir / "CommonCollectResult").write_text(_EDGE_SW02, encoding="utf-8")

    return site_dir
