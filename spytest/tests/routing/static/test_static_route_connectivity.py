"""
STATIC ROUTE CONNECTIVITY
Author: Athira
© 2024, copyrights@SuperMicro

How to run:
  ./bin/spytest --tryssh 1 \
  --testbed ./testbeds/testbed_Dvs.yaml \
  routing/static/test_static_route_connectivity.py \
  --logs-path ./logs/device-mgmt \
  --log-level debug --skip-init-config --ifname-type native

Description:
  Validates IPv4 static routing reachability for a single-hop topology.
  The test configures a point-to-point network between DUT1 and DUT2,
  assigns a second network on DUT2, adds a static route on DUT1 that
  points to DUT2, and finally verifies end-to-end connectivity using ICMP.

Pre-requisites:
  - Topology: D1D2:1 | Supported: HW and Virtual
  - Topology Diagram :
        # Topology - 2 nodes
        # +--------------------+                       +--------------------+
        # |        dut1        |=======================|        dut2        |
        # |   Ethernet32       |                       |   Ethernet32       |
        # |                    |                       |   Ethernet36       |
        # +--------------------+                       +--------------------+

  - Feature flags / min SONiC version: None
  - Required test variables (YAML): tests/routing/static/vars_static_route_connectivity.yaml
"""

from __future__ import annotations

from dataclasses import dataclass
from ipaddress import ip_interface
from pathlib import Path
from typing import Dict, Iterable, Tuple

import pytest
import yaml

from spytest import SpyTestDict, st
import apis.routing.ip as ip_api

VAR_FILE_ENV = "STATIC_ROUTE_VAR_FILE"
DEFAULT_VAR_FILE = (
    Path(__file__).resolve().parents[0] / "vars_static_route_connectivity.yaml"
)


def _load_yaml_data() -> Dict:
    """Load testcase configuration from YAML with environment override."""
    override = st.getenv(VAR_FILE_ENV)
    candidate = Path(override) if override else DEFAULT_VAR_FILE
    if not candidate.exists():
        raise FileNotFoundError(f"Static route variables file not found: {candidate}")
    with candidate.open(encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def _split_cidr(cidr: str) -> Tuple[str, int]:
    """Return IP address and prefix length from CIDR string."""
    iface = ip_interface(cidr)
    return str(iface.ip), int(iface.network.prefixlen)


def _iter_topology_aliases(topology: SpyTestDict) -> Iterable[str]:
    """Yield DUT aliases discovered inside topology object."""
    for alias in ("D1", "D2", "D3", "D4"):
        if hasattr(topology, alias):
            yield alias


@dataclass(frozen=True)
class InterfaceConfig:
    dut: str
    name: str
    address: str


@dataclass(frozen=True)
class StaticRouteConfig:
    dut: str
    prefix: str
    next_hop: str


@pytest.fixture(scope="class", autouse=True)
def static_route_suite_setup(request):
    """Provision static routing connectivity for the suite."""
    cls = request.cls
    cfg = SpyTestDict(_load_yaml_data())
    defaults = SpyTestDict(cfg.get("defaults", {}))

    min_topology = defaults.get("min_topology") or ["D1D2:1"]
    topology = st.ensure_min_topology(*min_topology)

    cls.data = SpyTestDict()
    cls.data.config = cfg
    cls.data.defaults = defaults
    cls.data.topology = topology
    cli_candidates = defaults.get("cli_type") or ["click"]
    preferred_cli = "click" if "click" in cli_candidates else cli_candidates[0]
    cls.data.cli_type = preferred_cli
    cls.data.route_cli_type = preferred_cli
    cls.data.verify_timeout = int(defaults.get("verify_timeout", 60))
    cls.data.cleanup = bool(defaults.get("cleanup", True))
    cls.data.dut_map = SpyTestDict(
        {alias: getattr(topology, alias) for alias in _iter_topology_aliases(topology)}
    )

    tc_key = "TC-IP-STATIC-001"
    cls.data.testcase_id = tc_key
    cls.data.testcase = SpyTestDict(cfg.get("testcases", {}).get(tc_key, {}))
    if not cls.data.testcase:
        raise ValueError(f"Missing testcase definition for id {tc_key}")

    dut1 = cls.data.dut_map.get("D1")
    dut2 = cls.data.dut_map.get("D2")
    if not (dut1 and dut2):
        raise ValueError("Both D1 and D2 must be present in topology for this suite")

    primary_intfs = [
        InterfaceConfig("D1", cls.data.testcase.dut1.interface, cls.data.testcase.dut1.address),
        InterfaceConfig("D2", cls.data.testcase.dut2.primary_interface, cls.data.testcase.dut2.primary_address),
        InterfaceConfig("D2", cls.data.testcase.dut2.secondary_interface, cls.data.testcase.dut2.secondary_address),
    ]
    cls.data.interface_configs = primary_intfs

    cls.data.static_route = StaticRouteConfig(
        dut="D1",
        prefix=cls.data.testcase.dut1.static_route.prefix,
        next_hop=cls.data.testcase.dut1.static_route.next_hop,
    )

    configured = []
    try:
        for entry in primary_intfs:
            ip_address, prefix_len = _split_cidr(entry.address)
            dut_handle = cls.data.dut_map[entry.dut]
            st.log(f"Configuring {entry.dut} interface {entry.name} with {entry.address}")
            if not ip_api.config_ip_addr_interface(
                dut_handle,
                interface_name=entry.name,
                ip_address=ip_address,
                subnet=prefix_len,
                family="ipv4",
                cli_type=cls.data.cli_type,
            ):
                raise RuntimeError(f"Failed to configure {entry.dut} {entry.name} with {entry.address}")
            configured.append((entry.dut, entry.name, ip_address, prefix_len))

        st.log(
            f"Adding static route {cls.data.static_route.prefix} via {cls.data.static_route.next_hop} on DUT1"
        )
        if not ip_api.create_static_route(
            cls.data.dut_map["D1"],
            static_ip=cls.data.static_route.prefix,
            next_hop=cls.data.static_route.next_hop,
            family="ipv4",
            cli_type=cls.data.route_cli_type,
        ):
            raise RuntimeError(
                f"Failed to create static route {cls.data.static_route.prefix} via {cls.data.static_route.next_hop}"
            )
        cls.data.configured_interfaces = configured
        cls.data.route_programmed = True
        yield
    finally:
        if getattr(cls.data, "route_programmed", False):
            st.log(f"Removing static route {cls.data.static_route.prefix} from DUT1")
            ip_api.delete_static_route(
                cls.data.dut_map["D1"],
                static_ip=cls.data.static_route.prefix,
                next_hop=cls.data.static_route.next_hop,
                family="ipv4",
                cli_type=cls.data.route_cli_type,
            )

        if cls.data.get("cleanup", True):
            for dut_alias, intf_name, ip_address, prefix_len in reversed(
                getattr(cls.data, "configured_interfaces", [])
            ):
                st.log(f"Removing IP {ip_address}/{prefix_len} from {dut_alias} {intf_name}")
                ip_api.config_ip_addr_interface(
                    cls.data.dut_map[dut_alias],
                    interface_name=intf_name,
                    ip_address=ip_address,
                    subnet=prefix_len,
                    family="ipv4",
                    cli_type=cls.data.cli_type,
                    config="remove",
                )


@pytest.mark.topology("any")
class TestStaticRouteConnectivity:
    """Testcases covering IPv4 static routing reachability via DUT2."""

    data: SpyTestDict

    def test_static_route_ping(self):
        """Ping DUT2 secondary network from DUT1 using configured static route."""
        ping_cfg = self.data.testcase.ping
        dut_handle = self.data.dut_map[ping_cfg.source_dut]
        st.log(
            f"Pinging {ping_cfg.target_ip} from {ping_cfg.source_dut} "
            f"using interface {ping_cfg.source_interface}"
        )
        wait_interval = 5
        attempts = max(1, self.data.verify_timeout // wait_interval)
        route_present = False
        try:
            for attempt in range(1, attempts + 1):
                if ip_api.verify_ip_route(
                    self.data.dut_map[self.data.static_route.dut],
                    family="ipv4",
                    ip_address=self.data.static_route.prefix,
                    type="S",
                    nexthop=self.data.static_route.next_hop,
                    cli_type=self.data.route_cli_type,
                ):
                    route_present = True
                    break
                st.log(
                    f"Static route {self.data.static_route.prefix} not present yet "
                    f"(attempt {attempt}/{attempts}); waiting {wait_interval}s"
                )
                st.wait(wait_interval, "Route programming grace period")
            assert route_present, (
                f"Static route {self.data.static_route.prefix} via {self.data.static_route.next_hop} "
                f"missing on {self.data.static_route.dut}"
            )

            result = ip_api.ping(
                dut_handle,
                ping_cfg.target_ip,
                family="ipv4",
                cli_type=self.data.cli_type,
                interface=ping_cfg.source_interface,
                count=5,
            )
            assert result, f"Ping to {ping_cfg.target_ip} from {ping_cfg.source_dut} failed via static route"
        except AssertionError as exc:
            st.report_tc_fail(self.data.testcase_id, str(exc))
            raise

        st.report_tc_pass(
            self.data.testcase_id,
            f"Static route {self.data.static_route.prefix} reachable via ping to {ping_cfg.target_ip}",
        )
