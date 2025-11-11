"""
BGP MULTI-HOP OVER LOOPBACKS - Test ID 2.4.8
Author: Athira
Year: 2025

How to run:
  ./bin/spytest  --tryssh 1  \
  --testbed ./testbeds/testbed_vs_2node.yaml  \
  tests/routing/BGP/test_bgp_multihop_over_loopbacks.py \
  --logs-path ./logs/test_bgp_multihop_over_loopbacks_$(date +%F_%H%M%S) \
  --log-level debug  --skip-init-config  --ifname-type native

Description:
  Comprehensive validation of BGP multi-hop configuration over loopback interfaces
  covering iBGP and eBGP scenarios with various TTL values and address families
  (IPv4/IPv6). The test suite provisions interfaces, loopbacks, static routes, BGP
  routers, and neighbors using SpyTest APIs, validates session establishment via
  'show ip bgp summary', and ensures complete cleanup. Supports klish (sonic-cli)
  mode. Each testcase is topology-aware and consumes variables from YAML to remain
  reusable across SONiC hardware and virtual environments.

Pre-requisites:
  - Topology: t0/t1/any | Supported: HW and Virtual
  - Topology Diagram :
        # Topology - 2 nodes
        # +----------------------+                   +----------------------+
        # |   D1 (smic_sonic1)   |===================|   D2 (smic_sonic2)   |
        # |    10.0.0.1/30       |     Ethernet4     |    10.0.0.2/30       |
        # |  Loopback0:          |                   |  Loopback0:          |
        # |    1.1.1.1/32        |                   |    2.2.2.2/32        |
        # +----------------------+                   +----------------------+

  - Feature flags / min SONiC version: BGP support required
  - Required test variables (YAML): vars_bgp_multihop_over_loopbacks.yaml
    - defaults.cli_type (klish)
    - defaults.verify_timeout (120 seconds recommended)
    - defaults.cleanup (true for cleanup after tests)
    - defaults.min_topology (D1D2:1)
    - testcases.* definitions for all 12 sub-testcases
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional
import re
import time

import pytest
import yaml

from spytest import SpyTestDict, st

import apis.routing.bgp as bgp_api
import apis.routing.ip as ip_api

VAR_FILE_ENV = "BGP_248_VAR_FILE"


def _candidate_var_files() -> List[Path]:
    """Return candidate YAML paths in search order."""
    candidates: List[Path] = []
    override = st.getenv(VAR_FILE_ENV)
    if override:
        candidates.append(Path(override))

    project_root = Path(__file__).resolve().parents[3]
    candidates.append(project_root / "vars" / "routing" / "bgp" / "vars_bgp_multihop_over_loopbacks.yaml")
    candidates.append(Path(__file__).resolve().with_name("vars_bgp_multihop_over_loopbacks.yaml"))
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
    st.report_fail("msg", f"BGP 2.4.8 variable file not found. Checked: {attempted_paths}")
    return SpyTestDict()


def _iter_candidate_duts(topology: SpyTestDict) -> Iterable[str]:
    """Yield topology keys that resemble DUT aliases (D1, D2, ...)."""
    for key, value in topology.items():
        if key.upper().startswith("D") and value:
            yield key


@pytest.mark.topology("any")
class TestBgpMultihopOverLoopbacks:
    """Testcases for validating BGP multi-hop over loopbacks - Test ID 2.4.8."""

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

        cli_types_raw = defaults.get("cli_type", "klish")
        if isinstance(cli_types_raw, str):
            cli_types = [ct.strip().lower() for ct in cli_types_raw.split(",") if ct.strip()]
        elif isinstance(cli_types_raw, list):
            cli_types = [str(ct).strip().lower() for ct in cli_types_raw if ct]
        else:
            cli_types = ["klish"]

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
        """Configure an IPv4/IPv6 address on an interface."""
        dut = self._resolve_dut(config.get("dut"))
        if not dut:
            st.report_fail("msg", f"Invalid DUT alias in interface config: {config}")

        interface = config.get("interface")
        ip_address = config.get("ip_address")
        prefix_length = config.get("prefix_length")
        family = config.get("family", "ipv4")
        cli_type = config.get("cli_type", "klish")

        result = ip_api.config_ip_addr_interface(
            dut,
            interface_name=interface,
            ip_address=ip_address,
            subnet=str(prefix_length),
            family=family,
            config="add",
            cli_type=cli_type,
        )

        if not result:
            st.report_fail("msg", f"Failed to configure {family} address {ip_address}/{prefix_length} on {interface} ({dut})")

        if config not in self._configured_interfaces:
            self._configured_interfaces.append(config)

        st.log(f"Configured {family} address {ip_address}/{prefix_length} on {interface} ({dut})")

    def _remove_interface_ip(self, config: SpyTestDict) -> None:
        """Remove an IPv4/IPv6 address from an interface."""
        dut = self._resolve_dut(config.get("dut"))
        if not dut:
            return

        interface = config.get("interface")
        ip_address = config.get("ip_address")
        prefix_length = config.get("prefix_length")
        family = config.get("family", "ipv4")
        cli_type = config.get("cli_type", "klish")

        ip_api.delete_ip_interface(
            dut,
            interface_name=interface,
            ip_address=ip_address,
            subnet=str(prefix_length),
            family=family,
            cli_type=cli_type,
        )

        st.log(f"Removed {family} address {ip_address}/{prefix_length} from {interface} ({dut})")

    def _configure_loopback_ip(self, config: SpyTestDict) -> None:
        """Configure a loopback interface with an IPv4/IPv6 address."""
        dut = self._resolve_dut(config.get("dut"))
        if not dut:
            st.report_fail("msg", f"Invalid DUT alias in loopback config: {config}")

        loopback = config.get("loopback")
        ip_address = config.get("ip_address")
        prefix_length = config.get("prefix_length")
        family = config.get("family", "ipv4")
        cli_type = config.get("cli_type", "klish")

        # Create loopback interface if needed
        result = ip_api.configure_loopback(
            dut,
            loopback_name=loopback,
            config="yes",
            cli_type=cli_type,
        )

        if not result:
            st.report_fail("msg", f"Failed to create {loopback} on {dut}")

        # Configure IP address on loopback
        result = ip_api.config_ip_addr_interface(
            dut,
            interface_name=loopback,
            ip_address=ip_address,
            subnet=str(prefix_length),
            family=family,
            config="add",
            cli_type=cli_type,
        )

        if not result:
            st.report_fail("msg", f"Failed to configure {family} address {ip_address}/{prefix_length} on {loopback} ({dut})")

        if config not in self._configured_loopbacks:
            self._configured_loopbacks.append(config)

        st.log(f"Configured {family} address {ip_address}/{prefix_length} on {loopback} ({dut})")

    def _remove_loopback_ip(self, config: SpyTestDict) -> None:
        """Remove a loopback interface and its IP address."""
        dut = self._resolve_dut(config.get("dut"))
        if not dut:
            return

        loopback = config.get("loopback")
        cli_type = config.get("cli_type", "klish")

        # Remove loopback interface
        ip_api.configure_loopback(
            dut,
            loopback_name=loopback,
            config="no",
            cli_type=cli_type,
        )

        st.log(f"Removed {loopback} from {dut}")

    def _configure_static_route(self, config: SpyTestDict) -> None:
        """Configure an IPv4/IPv6 static route."""
        dut = self._resolve_dut(config.get("dut"))
        if not dut:
            st.report_fail("msg", f"Invalid DUT alias in static route config: {config}")

        destination = config.get("destination")
        next_hop = config.get("next_hop")
        family = config.get("family", "ipv4")
        cli_type = config.get("cli_type", "klish")

        result = ip_api.create_static_route(
            dut,
            next_hop=next_hop,
            static_ip=destination,
            family=family,
            cli_type=cli_type,
        )

        if not result:
            st.report_fail("msg", f"Failed to configure {family} static route {destination} via {next_hop} on {dut}")

        if config not in self._configured_static_routes:
            self._configured_static_routes.append(config)

        st.log(f"Configured {family} static route {destination} via {next_hop} on {dut}")

    def _remove_static_route(self, config: SpyTestDict) -> None:
        """Remove an IPv4/IPv6 static route."""
        dut = self._resolve_dut(config.get("dut"))
        if not dut:
            return

        destination = config.get("destination")
        next_hop = config.get("next_hop")
        family = config.get("family", "ipv4")
        cli_type = config.get("cli_type", "klish")

        ip_api.delete_static_route(
            dut,
            next_hop=next_hop,
            static_ip=destination,
            family=family,
            cli_type=cli_type,
        )

        st.log(f"Removed {family} static route {destination} via {next_hop} from {dut}")

    def _configure_bgp_router(self, config: SpyTestDict) -> None:
        """Configure BGP router with ASN and router ID."""
        dut = self._resolve_dut(config.get("dut"))
        if not dut:
            st.report_fail("msg", f"Invalid DUT alias in BGP router config: {config}")

        local_asn = config.get("local_asn")
        router_id = config.get("router_id")
        cli_type = config.get("cli_type", "klish")

        # Configure BGP router
        result = bgp_api.config_bgp_router(
            dut,
            local_asn=local_asn,
            router_id=router_id,
            config="yes",
            cli_type=cli_type,
        )

        if not result:
            st.report_fail("msg", f"Failed to configure BGP router AS{local_asn} on {dut}")

        if config not in self._configured_routers:
            self._configured_routers.append(config)

        st.log(f"Configured BGP router AS{local_asn} with router-id {router_id} on {dut}")

    def _remove_bgp_router(self, config: SpyTestDict) -> None:
        """Remove BGP router configuration."""
        dut = self._resolve_dut(config.get("dut"))
        if not dut:
            return

        local_asn = config.get("local_asn")
        cli_type = config.get("cli_type", "klish")

        bgp_api.cleanup_router_bgp(dut, cli_type=cli_type)

        st.log(f"Removed BGP router AS{local_asn} from {dut}")

    def _configure_bgp_neighbor(self, config: SpyTestDict) -> None:
        """Configure BGP neighbor with all necessary parameters."""
        dut = self._resolve_dut(config.get("dut"))
        if not dut:
            st.report_fail("msg", f"Invalid DUT alias in BGP neighbor config: {config}")

        local_asn = config.get("local_asn")
        neighbor_ip = config.get("neighbor_ip")
        remote_asn = config.get("remote_asn")
        family = config.get("family", "ipv4")
        update_source = config.get("update_source")
        ebgp_multihop = config.get("ebgp_multihop")
        keepalive = config.get("keepalive")
        hold = config.get("hold")
        cli_type = config.get("cli_type", "klish")

        # Configure BGP neighbor
        result = bgp_api.create_bgp_neighbor(
            dut,
            local_asn,
            neighbor_ip,
            remote_asn,
            family=family,
            keep_alive=keepalive if keepalive else 60,
            hold=hold if hold else 180,
            cli_type=cli_type,
        )

        if not result:
            st.report_fail("msg", f"Failed to configure BGP neighbor {neighbor_ip} on {dut}")

        # Configure update-source using direct CLI (API has bugs with klish mode)
        if update_source:
            st.log(f"Configuring update-source {update_source} for neighbor {neighbor_ip} on {dut}")
            commands = [
                "configure terminal",
                f"router bgp {local_asn}",
                f"neighbor {neighbor_ip} update-source {update_source}",
                "end"
            ]
            try:
                st.config(dut, commands, type=cli_type)
            except Exception as e:
                st.report_fail("msg", f"Failed to configure update-source {update_source} for neighbor {neighbor_ip} on {dut}: {e}")

        # Configure ebgp-multihop using direct CLI (API has bugs with klish mode)
        if ebgp_multihop is not None:
            st.log(f"Configuring ebgp-multihop {ebgp_multihop} for neighbor {neighbor_ip} on {dut}")
            commands = [
                "configure terminal",
                f"router bgp {local_asn}",
                f"neighbor {neighbor_ip} ebgp-multihop {ebgp_multihop}",
                "end"
            ]
            try:
                st.config(dut, commands, type=cli_type)
            except Exception as e:
                st.report_fail("msg", f"Failed to configure ebgp-multihop {ebgp_multihop} for neighbor {neighbor_ip} on {dut}: {e}")

        # Configure timers if specified
        if keepalive is not None and hold is not None:
            result = bgp_api.config_bgp(
                dut,
                local_as=local_asn,
                neighbor=neighbor_ip,
                keepalive=str(keepalive),
                holdtime=str(hold),
                config="yes",
                cli_type=cli_type,
            )

            if not result:
                st.report_fail("msg", f"Failed to configure timers for neighbor {neighbor_ip} on {dut}")

        # Activate neighbor in address family
        if family == "ipv6":
            result = bgp_api.config_bgp(
                dut,
                local_as=local_asn,
                neighbor=neighbor_ip,
                addr_family="ipv6",
                config="yes",
                activate="yes",
                cli_type=cli_type,
            )

            if not result:
                st.report_fail("msg", f"Failed to activate IPv6 neighbor {neighbor_ip} on {dut}")
        else:
            result = bgp_api.config_bgp(
                dut,
                local_as=local_asn,
                neighbor=neighbor_ip,
                addr_family="ipv4",
                config="yes",
                activate="yes",
                cli_type=cli_type,
            )

            if not result:
                st.report_fail("msg", f"Failed to activate IPv4 neighbor {neighbor_ip} on {dut}")

        if config not in self._configured_neighbors:
            self._configured_neighbors.append(config)

        st.log(f"Configured BGP neighbor {neighbor_ip} (AS{remote_asn}) on {dut}")

    def _remove_bgp_neighbor(self, config: SpyTestDict) -> None:
        """Remove BGP neighbor configuration."""
        dut = self._resolve_dut(config.get("dut"))
        if not dut:
            return

        local_asn = config.get("local_asn")
        neighbor_ip = config.get("neighbor_ip")
        cli_type = config.get("cli_type", "klish")

        bgp_api.config_bgp(
            dut,
            local_as=local_asn,
            neighbor=neighbor_ip,
            config="no",
            cli_type=cli_type,
        )

        st.log(f"Removed BGP neighbor {neighbor_ip} from {dut}")

    def _verify_bgp_session(self, verify_config: SpyTestDict, timeout: Optional[int] = None) -> bool:
        """Verify BGP session state (Established or specific state)."""
        dut = self._resolve_dut(verify_config.get("dut"))
        if not dut:
            st.report_fail("msg", f"Invalid DUT alias in BGP verification: {verify_config}")

        neighbor_ip = verify_config.get("neighbor_ip")
        family = verify_config.get("family", "ipv4")
        expected_state = verify_config.get("state", "Established")
        expected_result = verify_config.get("expected", "established")
        verify_timeout = timeout or self.data.verify_timeout

        st.log(f"Verifying BGP session {neighbor_ip} on {dut}, expected state: {expected_state}")

        # For negative tests expecting not_established
        if expected_result == "not_established":
            # Wait and verify session does NOT reach Established state
            time.sleep(10)  # Allow time for connection attempts

            output = bgp_api.show_bgp_ipv4_summary(dut) if family == "ipv4" else bgp_api.show_bgp_ipv6_summary(dut)

            # Check if neighbor is in output
            neighbor_found = False
            if output:
                for entry in output:
                    if entry.get("neighbor") == neighbor_ip:
                        neighbor_found = True
                        state = entry.get("state", "")
                        # Verify state is NOT Established
                        if "Established" in state or state.isdigit():
                            st.log(f"FAILED: Neighbor {neighbor_ip} unexpectedly reached Established state")
                            return False
                        st.log(f"SUCCESS: Neighbor {neighbor_ip} is in expected non-Established state: {state}")
                        return True

            if not neighbor_found:
                st.log(f"SUCCESS: Neighbor {neighbor_ip} not found or in expected non-Established state")
                return True

            return True

        # For positive tests expecting Established state
        def _check_established() -> bool:
            output = bgp_api.show_bgp_ipv4_summary(dut) if family == "ipv4" else bgp_api.show_bgp_ipv6_summary(dut)

            if not output:
                return False

            for entry in output:
                if entry.get("neighbor") == neighbor_ip:
                    state = entry.get("state", "")
                    # Check if state is Established (indicated by uptime or "Established")
                    if "Established" in state or state.isdigit():
                        st.log(f"BGP session {neighbor_ip} is Established on {dut}")
                        return True
                    st.log(f"BGP session {neighbor_ip} is in state: {state}")

            return False

        # Poll for session establishment
        if st.poll_wait(_check_established, verify_timeout, interval=5):
            return True

        st.log(f"BGP session {neighbor_ip} did not reach Established state within {verify_timeout}s on {dut}")
        return False

    def _execute_testcase(self, tcid: str) -> None:
        """Execute a test case by ID."""
        testcase = self.data.testcases.get(tcid)
        if not testcase:
            st.report_fail("msg", f"Testcase {tcid} not found in YAML configuration")

        st.log(f"=== Executing Test {tcid}: {testcase.get('title')} ===")
        st.log(f"Description: {testcase.get('description')}")

        setup_steps = testcase.get("setup", [])
        verify_steps = testcase.get("verify", [])
        cli_type = testcase.get("cli_type", "klish")

        # Execute setup steps in order
        for step in setup_steps:
            step_dict = SpyTestDict(step)
            step_dict.cli_type = cli_type
            step_type = step_dict.get("type")

            if step_type == "interface":
                self._configure_interface_ip(step_dict)
            elif step_type == "loopback":
                self._configure_loopback_ip(step_dict)
            elif step_type == "static_route":
                self._configure_static_route(step_dict)
            elif step_type == "bgp_router":
                self._configure_bgp_router(step_dict)
            elif step_type == "bgp_neighbor":
                self._configure_bgp_neighbor(step_dict)
            else:
                st.warn(f"Unknown setup step type: {step_type}")

        # Wait for BGP sessions to converge
        st.log(f"Waiting for BGP sessions to converge...")
        time.sleep(5)

        # Execute verification steps
        all_verified = True
        for verify_step in verify_steps:
            verify_dict = SpyTestDict(verify_step)
            if not self._verify_bgp_session(verify_dict):
                all_verified = False
                st.log(f"Verification failed for neighbor {verify_dict.get('neighbor_ip')} on {verify_dict.get('dut')}")

        if all_verified:
            st.log(f"=== Test {tcid} PASSED ===")
            st.report_pass("test_case_passed")
        else:
            st.log(f"=== Test {tcid} FAILED ===")
            st.report_fail("msg", f"Test {tcid} failed: BGP session verification failed")

    # ========================================================================
    # Test Cases
    # ========================================================================

    @pytest.mark.inventory(feature="Regression", testcases=["BGP_248_TC2.4.8.1"])
    def test_ibgp_ipv4_multihop_basic(self) -> None:
        """TC 2.4.8.1 – iBGP IPv4 Multi-hop Over Loopbacks (Basic)."""
        self._execute_testcase("2.4.8.1")

    @pytest.mark.inventory(feature="Regression", testcases=["BGP_248_TC2.4.8.2"])
    def test_ebgp_ipv4_multihop_ttl2(self) -> None:
        """TC 2.4.8.2 – eBGP IPv4 Multi-hop Over Loopbacks (TTL=2)."""
        self._execute_testcase("2.4.8.2")

    @pytest.mark.inventory(feature="Regression", testcases=["BGP_248_TC2.4.8.3"])
    def test_ebgp_ipv4_multihop_ttl3(self) -> None:
        """TC 2.4.8.3 – eBGP IPv4 Multi-hop Over Loopbacks (TTL=3)."""
        self._execute_testcase("2.4.8.3")

    @pytest.mark.inventory(feature="Regression", testcases=["BGP_248_TC2.4.8.4"])
    def test_ebgp_ipv4_multihop_ttl255(self) -> None:
        """TC 2.4.8.4 – eBGP IPv4 Multi-hop Over Loopbacks (TTL=255, Maximum)."""
        self._execute_testcase("2.4.8.4")

    @pytest.mark.inventory(feature="Regression", testcases=["BGP_248_TC2.4.8.5"])
    def test_ibgp_ipv6_multihop(self) -> None:
        """TC 2.4.8.5 – iBGP IPv6 Multi-hop Over Loopbacks."""
        self._execute_testcase("2.4.8.5")

    @pytest.mark.inventory(feature="Regression", testcases=["BGP_248_TC2.4.8.6"])
    def test_ebgp_ipv6_multihop_ttl2(self) -> None:
        """TC 2.4.8.6 – eBGP IPv6 Multi-hop Over Loopbacks (TTL=2)."""
        self._execute_testcase("2.4.8.6")

    @pytest.mark.inventory(feature="Regression", testcases=["BGP_248_TC2.4.8.7"])
    @pytest.mark.negative
    def test_ebgp_multihop_insufficient_ttl(self) -> None:
        """TC 2.4.8.7 – Negative: eBGP Multi-hop with Insufficient TTL."""
        self._execute_testcase("2.4.8.7")

    @pytest.mark.inventory(feature="Regression", testcases=["BGP_248_TC2.4.8.8"])
    @pytest.mark.negative
    def test_ebgp_without_multihop_config(self) -> None:
        """TC 2.4.8.8 – Negative: eBGP Without Multi-hop Configuration."""
        self._execute_testcase("2.4.8.8")

    @pytest.mark.inventory(feature="Regression", testcases=["BGP_248_TC2.4.8.9"])
    def test_ebgp_ipv4_multiple_loopbacks(self) -> None:
        """TC 2.4.8.9 – eBGP IPv4 Multi-hop with Multiple Loopbacks."""
        self._execute_testcase("2.4.8.9")

    @pytest.mark.inventory(feature="Regression", testcases=["BGP_248_TC2.4.8.10"])
    def test_ebgp_ipv6_multihop_ttl255(self) -> None:
        """TC 2.4.8.10 – eBGP IPv6 Multi-hop with Maximum TTL (255)."""
        self._execute_testcase("2.4.8.10")

    @pytest.mark.inventory(feature="Regression", testcases=["BGP_248_TC2.4.8.11"])
    def test_multihop_session_stability_route_changes(self) -> None:
        """TC 2.4.8.11 – Multi-hop Session Stability with Route Changes."""
        self._execute_testcase("2.4.8.11")

    @pytest.mark.inventory(feature="Regression", testcases=["BGP_248_TC2.4.8.12"])
    def test_multihop_custom_timers(self) -> None:
        """TC 2.4.8.12 – Multi-hop with BGP Timers Customization."""
        self._execute_testcase("2.4.8.12")
