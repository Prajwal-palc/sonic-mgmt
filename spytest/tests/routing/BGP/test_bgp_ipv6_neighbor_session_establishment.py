"""
BGP IPv6 NEIGHBOR SESSION ESTABLISHMENT - Test ID 2.4.2
Author: QA Team
© 2025, copyrights@SuperMicro

How to run:
  ./bin/spytest  --tryssh 1  \
  --testbed ./testbeds/testbed_vs_2node.yaml  \
  tests/routing/BGP/test_bgp_ipv6_neighbor_session_establishment.py \
  --logs-path ./logs/test_bgp_ipv6_neighbor_session_establishment_$(date +%F_%H%M%S) \
  --log-level debug  --skip-init-config  --ifname-type native

Description:
  Comprehensive validation of IPv6 BGP neighbor session establishment across multiple
  scenarios including iBGP/eBGP, numbered/unnumbered interfaces, and loopback-based/
  direct back-to-back peering. The test suite provisions interfaces, loopbacks, BGP
  routers, and neighbors using SpyTest APIs, validates session establishment via
  'show bgp ipv6 summary', and ensures complete cleanup. Supports both click and klish
  (sonic-cli) modes. Each testcase is topology-aware and consumes variables from YAML
  to remain reusable across SONiC hardware and virtual environments.

Pre-requisites:
  - Topology: t0/t1/any | Supported: HW and Virtual
  - Topology Diagram :
        # Topology - 2 nodes
        # +----------------------+                   +----------------------+
        # |   D1 (smic_sonic1)   |===================|   D2 (smic_sonic2)   |
        # |      (IPv6)          |     Ethernet4     |      (IPv6)          |
        # +----------------------+                   +----------------------+

  - Feature flags / min SONiC version: BGP IPv6 support required
  - Required test variables (YAML): vars_bgp_ipv6_neighbor_session_establishment.yaml
    - defaults.cli_type (click, klish)
    - defaults.verify_timeout (120 seconds recommended)
    - defaults.cleanup (true for cleanup after tests)
    - defaults.min_topology (D1D2:1)
    - testcases.* definitions for all 8 sub-testcases
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

import pytest
import yaml

from spytest import SpyTestDict, st

import apis.routing.bgp as bgp_api
import apis.routing.ip as ip_api

VAR_FILE_ENV = "BGP_242_VAR_FILE"


def _candidate_var_files() -> List[Path]:
    """Return candidate YAML paths in search order."""
    candidates: List[Path] = []
    override = st.getenv(VAR_FILE_ENV)
    if override:
        candidates.append(Path(override))

    project_root = Path(__file__).resolve().parents[3]
    candidates.append(project_root / "vars" / "routing" / "bgp" / "vars_bgp_ipv6_neighbor_session_establishment.yaml")
    candidates.append(Path(__file__).resolve().with_name("vars_bgp_ipv6_neighbor_session_establishment.yaml"))
    return candidates


def _load_yaml_data() -> SpyTestDict:
    """Load testcase variables from the first available YAML file."""
    attempted: List[Path] = []
    for candidate in _candidate_var_files():
        attempted.append(candidate)
        if candidate.is_file():
            with candidate.open(encoding="utf-8") as handle:
                return SpyTestDict(yaml.safe_load(handle) or {})

    attempted_paths = ", ".join(str(path) for path in attempted)
    st.report_fail("msg", f"BGP 2.4.2 variable file not found. Checked: {attempted_paths}")
    return SpyTestDict()


def _iter_candidate_duts(topology: SpyTestDict) -> Iterable[str]:
    """Yield topology keys that resemble DUT aliases (D1, D2, ...)."""
    for key, value in topology.items():
        if key.upper().startswith("D") and value:
            yield key


@pytest.mark.topology("any")
class TestBgpIpv6NeighborSessionEstablishment:
    """Testcases for validating IPv6 BGP neighbor session establishment - Test ID 2.4.2."""

    data = SpyTestDict()

    @classmethod
    def setup_class(cls) -> None:
        """Load YAML configuration, topology, and defaults."""
        config = _load_yaml_data()
        defaults = SpyTestDict(config.get("defaults", {}))
        testcases = SpyTestDict(config.get("testcases", {}))

        min_topology = defaults.get("min_topology") or ["D1D2:1"]
        topology = st.ensure_min_topology(*min_topology)

        cls.data.config = config
        cls.data.defaults = defaults
        cls.data.testcases = testcases
        cls.data.topology = topology
        cls.data.dut_names = st.get_dut_names()
        cls.data.verify_timeout = int(defaults.get("verify_timeout", 120))
        cls.data.keepalive = int(defaults.get("keepalive", 60))
        cls.data.hold = int(defaults.get("hold", 180))

        cli_types_raw = defaults.get("cli_type", "click,klish")
        if isinstance(cli_types_raw, str):
            cli_types = [ct.strip().lower() for ct in cli_types_raw.split(",") if ct.strip()]
        elif isinstance(cli_types_raw, list):
            cli_types = [str(ct).strip().lower() for ct in cli_types_raw if ct]
        else:
            cli_types = ["click", "klish"]

        cls.data.cli_types = cli_types
        cls.data.cleanup = bool(defaults.get("cleanup", True))
        cls.data.dut_map = SpyTestDict()

        for alias in _iter_candidate_duts(topology):
            cls.data.dut_map[alias] = getattr(topology, alias)

    def setup_method(self) -> None:
        """Initialise per-test tracking and preconditions."""
        self._configured_interfaces: List[SpyTestDict] = []
        self._configured_loopbacks: List[SpyTestDict] = []
        self._configured_static_routes: List[SpyTestDict] = []
        self._configured_neighbors: List[SpyTestDict] = []
        self._configured_routers: List[SpyTestDict] = []

    def teardown_method(self) -> None:
        """Cleanup all dynamic configuration pushed during the test."""
        if not self.data.get("cleanup", True):
            return

        # Remove BGP neighbors
        while self._configured_neighbors:
            entry = self._configured_neighbors.pop()
            self._remove_bgp_neighbor(entry)

        # Remove BGP routers
        while self._configured_routers:
            router = self._configured_routers.pop()
            self._remove_bgp_router(router)

        # Remove static routes
        while self._configured_static_routes:
            route = self._configured_static_routes.pop()
            self._remove_static_route(route)

        # Remove loopback IPs
        while self._configured_loopbacks:
            lb = self._configured_loopbacks.pop()
            self._remove_loopback_ip(lb)

        # Remove interface IPs
        while self._configured_interfaces:
            iface = self._configured_interfaces.pop()
            self._remove_interface_ip(iface)

    def _resolve_dut(self, alias: str | None) -> str | None:
        """Translate a topology alias (e.g., D1) to the framework DUT handle."""
        if not alias:
            return None
        if alias in self.data.dut_map:
            return self.data.dut_map[alias]
        if alias in self.data.dut_names:
            return alias
        st.warn(f"Unable to resolve DUT alias '{alias}'")
        return None

    def _configure_interface_ip(self, config: SpyTestDict) -> None:
        """Configure an IPv6 address on an interface."""
        dut = self._resolve_dut(config.get("dut"))
        if not dut:
            st.report_fail("msg", f"Invalid DUT alias in interface config: {config}")

        interface = config.get("interface")
        ip_address = config.get("ip_address")
        prefix_length = config.get("prefix_length")
        cli_type = config.get("cli_type", "klish")

        result = ip_api.config_ip_addr_interface(
            dut,
            interface_name=interface,
            ip_address=ip_address,
            subnet=str(prefix_length),
            family="ipv6",
            config="add",
            cli_type=cli_type,
        )

        if not result:
            st.report_fail("msg", f"Failed to configure IPv6 {ip_address}/{prefix_length} on {dut}:{interface}")

        self._configured_interfaces.append(config)
        st.log(f"Configured IPv6 {ip_address}/{prefix_length} on {dut}:{interface}")

    def _remove_interface_ip(self, config: SpyTestDict) -> None:
        """Remove an IPv6 address from an interface."""
        dut = self._resolve_dut(config.get("dut"))
        if not dut:
            return

        interface = config.get("interface")
        ip_address = config.get("ip_address")
        prefix_length = config.get("prefix_length")
        cli_type = config.get("cli_type", "klish")

        ip_api.config_ip_addr_interface(
            dut,
            interface_name=interface,
            ip_address=ip_address,
            subnet=str(prefix_length),
            family="ipv6",
            config="remove",
            cli_type=cli_type,
        )

    def _configure_loopback_ip(self, config: SpyTestDict) -> None:
        """Configure a loopback interface with IPv6 address."""
        dut = self._resolve_dut(config.get("dut"))
        if not dut:
            st.report_fail("msg", f"Invalid DUT alias in loopback config: {config}")

        loopback = config.get("loopback")
        ip_address = config.get("ip_address")
        prefix_length = config.get("prefix_length")
        cli_type = config.get("cli_type", "klish")

        result = ip_api.config_ip_addr_interface(
            dut,
            interface_name=loopback,
            ip_address=ip_address,
            subnet=str(prefix_length),
            family="ipv6",
            config="add",
            cli_type=cli_type,
        )

        if not result:
            st.report_fail("msg", f"Failed to configure loopback IPv6 {ip_address}/{prefix_length} on {dut}:{loopback}")

        self._configured_loopbacks.append(config)
        st.log(f"Configured loopback IPv6 {ip_address}/{prefix_length} on {dut}:{loopback}")

    def _remove_loopback_ip(self, config: SpyTestDict) -> None:
        """Remove a loopback interface IPv6 address."""
        dut = self._resolve_dut(config.get("dut"))
        if not dut:
            return

        loopback = config.get("loopback")
        ip_address = config.get("ip_address")
        prefix_length = config.get("prefix_length")
        cli_type = config.get("cli_type", "klish")

        ip_api.config_ip_addr_interface(
            dut,
            interface_name=loopback,
            ip_address=ip_address,
            subnet=str(prefix_length),
            family="ipv6",
            config="remove",
            cli_type=cli_type,
        )

    def _configure_static_route(self, config: SpyTestDict) -> None:
        """Configure a static IPv6 route."""
        dut = self._resolve_dut(config.get("dut"))
        if not dut:
            st.report_fail("msg", f"Invalid DUT alias in static route config: {config}")

        destination = config.get("destination")
        next_hop = config.get("next_hop")
        cli_type = config.get("cli_type", "klish")

        result = ip_api.create_static_route(
            dut,
            next_hop=next_hop,
            static_ip=destination,
            family="ipv6",
            cli_type=cli_type,
        )

        if not result:
            st.report_fail("msg", f"Failed to configure static IPv6 route {destination} via {next_hop} on {dut}")

        self._configured_static_routes.append(config)
        st.log(f"Configured static IPv6 route {destination} via {next_hop} on {dut}")

    def _remove_static_route(self, config: SpyTestDict) -> None:
        """Remove a static IPv6 route."""
        dut = self._resolve_dut(config.get("dut"))
        if not dut:
            return

        destination = config.get("destination")
        next_hop = config.get("next_hop")
        cli_type = config.get("cli_type", "klish")

        ip_api.delete_static_route(
            dut,
            next_hop=next_hop,
            static_ip=destination,
            family="ipv6",
            cli_type=cli_type,
        )

    def _configure_bgp_router(self, config: SpyTestDict) -> None:
        """Configure BGP router context."""
        dut = self._resolve_dut(config.get("dut"))
        if not dut:
            st.report_fail("msg", f"Invalid DUT alias in BGP router config: {config}")

        local_asn = config.get("local_asn")
        router_id = config.get("router_id")
        cli_type = config.get("cli_type", "klish")
        vrf = config.get("vrf", "default")

        result = bgp_api.config_bgp_router(
            dut,
            local_asn=local_asn,
            router_id=router_id,
            keep_alive=self.data.keepalive,
            hold=self.data.hold,
            config="yes",
            vrf=vrf,
            cli_type=cli_type,
            ebgp_req_policy=False,
        )

        if not result:
            st.report_fail("msg", f"Failed to configure BGP router ASN {local_asn} on {dut}")

        self._configured_routers.append(config)
        st.log(f"Configured BGP router ASN {local_asn} with router-id {router_id} on {dut}")

    def _remove_bgp_router(self, config: SpyTestDict) -> None:
        """Remove BGP router context."""
        dut = self._resolve_dut(config.get("dut"))
        if not dut:
            return

        local_asn = config.get("local_asn")
        vrf = config.get("vrf", "default")
        cli_type = config.get("cli_type", "klish")

        bgp_api.config_router_bgp_mode(
            dut,
            local_asn=local_asn,
            config_mode="disable",
            vrf=vrf,
            cli_type=cli_type,
        )

    def _configure_bgp_neighbor(self, config: SpyTestDict) -> None:
        """Configure BGP IPv6 neighbor."""
        dut = self._resolve_dut(config.get("dut"))
        if not dut:
            st.report_fail("msg", f"Invalid DUT alias in BGP neighbor config: {config}")

        local_asn = config.get("local_asn")
        neighbor_ip = config.get("neighbor_ip")
        remote_asn = config.get("remote_asn")
        cli_type = config.get("cli_type", "klish")
        vrf = config.get("vrf", "default")
        update_source = config.get("update_source")
        ebgp_multihop = config.get("ebgp_multihop")

        # Create BGP neighbor for IPv6
        result = bgp_api.create_bgp_neighbor(
            dut,
            local_asn,
            neighbor_ip,
            remote_asn,
            keep_alive=self.data.keepalive,
            hold=self.data.hold,
            family="ipv6",
            vrf=vrf,
            cli_type=cli_type,
        )

        if not result:
            st.report_fail("msg", f"Failed to configure BGP IPv6 neighbor {neighbor_ip} on {dut}")

        # Activate IPv6 unicast address family for the neighbor
        # This is required for IPv6 BGP to establish sessions
        bgp_api.config_bgp(
            dut,
            local_asn=local_asn,
            neighbor=neighbor_ip,
            config="yes",
            config_type_list=["activate"],
            addr_family="ipv6",
            vrf_name=vrf,
            cli_type=cli_type,
        )

        # Configure update-source if specified
        if update_source:
            bgp_api.config_bgp(
                dut,
                local_asn=local_asn,
                neighbor=neighbor_ip,
                config="yes",
                config_type_list=["update_src"],
                update_src=update_source,
                addr_family="ipv6",
                vrf_name=vrf,
                cli_type=cli_type,
            )

        # Configure ebgp-multihop if specified
        if ebgp_multihop:
            bgp_api.config_bgp(
                dut,
                local_asn=local_asn,
                neighbor=neighbor_ip,
                config="yes",
                config_type_list=["ebgp_mhop"],
                ebgp_mhop=str(ebgp_multihop),
                addr_family="ipv6",
                vrf_name=vrf,
                cli_type=cli_type,
            )

        self._configured_neighbors.append(config)
        st.log(f"Configured BGP IPv6 neighbor {neighbor_ip} (remote-as {remote_asn}) on {dut}")

    def _configure_bgp_neighbor_interface(self, config: SpyTestDict) -> None:
        """Configure BGP neighbor using interface (unnumbered/link-local)."""
        dut = self._resolve_dut(config.get("dut"))
        if not dut:
            st.report_fail("msg", f"Invalid DUT alias in BGP neighbor config: {config}")

        local_asn = config.get("local_asn")
        interface = config.get("interface")
        remote_asn = config.get("remote_asn")
        cli_type = config.get("cli_type", "klish")
        vrf = config.get("vrf", "default")

        # For interface-based neighbors, use neighbor interface command
        result = bgp_api.config_bgp(
            dut,
            local_asn=local_asn,
            neighbor=interface,
            config="yes",
            remote_asn=remote_asn,
            interface=interface,
            config_type_list=["neighbor", "activate"],
            addr_family="ipv6",
            vrf_name=vrf,
            cli_type=cli_type,
        )

        if not result:
            st.report_fail("msg", f"Failed to configure BGP IPv6 neighbor on interface {interface} on {dut}")

        self._configured_neighbors.append(config)
        st.log(f"Configured BGP IPv6 unnumbered neighbor on {interface} (remote-as {remote_asn}) on {dut}")

    def _remove_bgp_neighbor(self, config: SpyTestDict) -> None:
        """Remove BGP neighbor."""
        dut = self._resolve_dut(config.get("dut"))
        if not dut:
            return

        local_asn = config.get("local_asn")
        neighbor_ip = config.get("neighbor_ip")
        interface = config.get("interface")
        remote_asn = config.get("remote_asn")
        vrf = config.get("vrf", "default")
        cli_type = config.get("cli_type", "klish")

        neighbor = neighbor_ip if neighbor_ip else interface

        bgp_api.delete_bgp_neighbor(
            dut,
            local_asn,
            neighbor,
            remote_asn,
            vrf=vrf,
            cli_type=cli_type,
        )

    def _verify_bgp_session_established(self, config: SpyTestDict) -> None:
        """Verify BGP IPv6 session reaches Established state."""
        dut = self._resolve_dut(config.get("dut"))
        if not dut:
            st.report_fail("msg", f"Invalid DUT alias in verification: {config}")

        neighbor_ip = config.get("neighbor_ip")
        interface = config.get("interface")
        cli_type = config.get("cli_type", "klish")
        vrf = config.get("vrf", "default")

        neighbor = neighbor_ip if neighbor_ip else interface

        def _check_established() -> bool:
            return bgp_api.verify_bgp_summary(
                dut,
                family="ipv6",
                neighbor=neighbor,
                state="Established",
                vrf=vrf,
                cli_type=cli_type,
            )

        if not st.poll_wait(_check_established, self.data.verify_timeout):
            st.report_fail("msg", f"BGP IPv6 session with {neighbor} did not reach Established state on {dut}")

        st.log(f"BGP IPv6 session with {neighbor} is Established on {dut}")

    def _get_testcase(self, tcid: str) -> SpyTestDict:
        """Helper to fetch testcase definition from YAML."""
        testcase = self.data.testcases.get(tcid)
        if not testcase:
            st.report_fail("msg", f"Missing testcase definition for {tcid} in YAML")
        return SpyTestDict(testcase)

    def _execute_testcase(self, tcid: str, cli_type: str) -> None:
        """Common execution logic for all testcases."""
        testcase = self._get_testcase(tcid)
        st.log(f"Executing testcase {tcid} with cli_type={cli_type}")

        # Configure interfaces
        for iface_cfg in testcase.get("interfaces", []):
            config = SpyTestDict(iface_cfg)
            config.cli_type = cli_type
            self._configure_interface_ip(config)

        # Configure loopbacks
        for lb_cfg in testcase.get("loopbacks", []):
            config = SpyTestDict(lb_cfg)
            config.cli_type = cli_type
            self._configure_loopback_ip(config)

        # Configure static routes
        for route_cfg in testcase.get("static_routes", []):
            config = SpyTestDict(route_cfg)
            config.cli_type = cli_type
            self._configure_static_route(config)

        # Configure BGP routers
        for router_cfg in testcase.get("bgp_routers", []):
            config = SpyTestDict(router_cfg)
            config.cli_type = cli_type
            self._configure_bgp_router(config)

        # Configure BGP neighbors (IP-based or interface-based)
        for neighbor_cfg in testcase.get("bgp_neighbors", []):
            config = SpyTestDict(neighbor_cfg)
            config.cli_type = cli_type
            if config.get("neighbor_ip"):
                self._configure_bgp_neighbor(config)
            else:
                self._configure_bgp_neighbor_interface(config)

        # Wait for sessions to stabilize
        st.wait(10, "Waiting for BGP IPv6 sessions to stabilize")

        # Verify BGP sessions
        for neighbor_cfg in testcase.get("bgp_neighbors", []):
            config = SpyTestDict(neighbor_cfg)
            config.cli_type = cli_type
            self._verify_bgp_session_established(config)

    @pytest.mark.inventory(feature="Regression", testcases=["BGP_2.4.2.1"])
    def test_ibgp_ipv6_numbered_loopback(self) -> None:
        """Test ID 2.4.2.1 - iBGP IPv6 Numbered (Loopback-Based)."""
        for cli_type in self.data.cli_types:
            st.log(f"Running test_ibgp_ipv6_numbered_loopback with cli_type={cli_type}")
            self._execute_testcase("2.4.2.1", cli_type)
            # Cleanup for next iteration
            self.teardown_method()
            self.setup_method()
        st.report_pass("test_case_passed")

    @pytest.mark.inventory(feature="Regression", testcases=["BGP_2.4.2.2"])
    def test_ibgp_ipv6_unnumbered_loopback(self) -> None:
        """Test ID 2.4.2.2 - iBGP IPv6 Unnumbered (Loopback-Based)."""
        for cli_type in self.data.cli_types:
            st.log(f"Running test_ibgp_ipv6_unnumbered_loopback with cli_type={cli_type}")
            self._execute_testcase("2.4.2.2", cli_type)
            self.teardown_method()
            self.setup_method()
        st.report_pass("test_case_passed")

    @pytest.mark.inventory(feature="Regression", testcases=["BGP_2.4.2.3"])
    def test_ebgp_ipv6_numbered_loopback(self) -> None:
        """Test ID 2.4.2.3 - eBGP IPv6 Numbered (Loopback-Based)."""
        for cli_type in self.data.cli_types:
            st.log(f"Running test_ebgp_ipv6_numbered_loopback with cli_type={cli_type}")
            self._execute_testcase("2.4.2.3", cli_type)
            self.teardown_method()
            self.setup_method()
        st.report_pass("test_case_passed")

    @pytest.mark.inventory(feature="Regression", testcases=["BGP_2.4.2.4"])
    def test_ebgp_ipv6_unnumbered_loopback(self) -> None:
        """Test ID 2.4.2.4 - eBGP IPv6 Unnumbered (Loopback-Based)."""
        for cli_type in self.data.cli_types:
            st.log(f"Running test_ebgp_ipv6_unnumbered_loopback with cli_type={cli_type}")
            self._execute_testcase("2.4.2.4", cli_type)
            self.teardown_method()
            self.setup_method()
        st.report_pass("test_case_passed")

    @pytest.mark.inventory(feature="Regression", testcases=["BGP_2.4.2.5"])
    def test_ibgp_ipv6_numbered_direct(self) -> None:
        """Test ID 2.4.2.5 - iBGP IPv6 Numbered (Direct Back-to-Back)."""
        for cli_type in self.data.cli_types:
            st.log(f"Running test_ibgp_ipv6_numbered_direct with cli_type={cli_type}")
            self._execute_testcase("2.4.2.5", cli_type)
            self.teardown_method()
            self.setup_method()
        st.report_pass("test_case_passed")

    @pytest.mark.inventory(feature="Regression", testcases=["BGP_2.4.2.6"])
    def test_ibgp_ipv6_unnumbered_direct(self) -> None:
        """Test ID 2.4.2.6 - iBGP IPv6 Unnumbered (Direct Back-to-Back)."""
        for cli_type in self.data.cli_types:
            st.log(f"Running test_ibgp_ipv6_unnumbered_direct with cli_type={cli_type}")
            self._execute_testcase("2.4.2.6", cli_type)
            self.teardown_method()
            self.setup_method()
        st.report_pass("test_case_passed")

    @pytest.mark.inventory(feature="Regression", testcases=["BGP_2.4.2.7"])
    def test_ebgp_ipv6_numbered_direct(self) -> None:
        """Test ID 2.4.2.7 - eBGP IPv6 Numbered (Direct Back-to-Back)."""
        for cli_type in self.data.cli_types:
            st.log(f"Running test_ebgp_ipv6_numbered_direct with cli_type={cli_type}")
            self._execute_testcase("2.4.2.7", cli_type)
            self.teardown_method()
            self.setup_method()
        st.report_pass("test_case_passed")

    @pytest.mark.inventory(feature="Regression", testcases=["BGP_2.4.2.8"])
    def test_ebgp_ipv6_unnumbered_direct(self) -> None:
        """Test ID 2.4.2.8 - eBGP IPv6 Unnumbered (Direct Back-to-Back)."""
        for cli_type in self.data.cli_types:
            st.log(f"Running test_ebgp_ipv6_unnumbered_direct with cli_type={cli_type}")
            self._execute_testcase("2.4.2.8", cli_type)
            self.teardown_method()
            self.setup_method()
        st.report_pass("test_case_passed")
