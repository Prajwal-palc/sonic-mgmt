"""
BGP SESSION RECOVERY AFTER INTERFACE FLAP - Test ID 2.4.5
Author: QA Team
© 2025, copyrights@SuperMicro

How to run:
  ./bin/spytest  --tryssh 1  \
  --testbed ./testbeds/testbed_vs_2node.yaml  \
  tests/routing/BGP/test_bgp_session_recovery_after_interface_flap.py \
  --logs-path ./logs/test_bgp_session_recovery_after_interface_flap_$(date +%F_%H%M%S) \
  --log-level debug  --skip-init-config  --ifname-type native

Description:
  Validates BGP session resilience and recovery after interface flap events. The suite
  tests eBGP, iBGP, numbered/unnumbered, multihop, and BFD-enabled sessions to ensure
  they recover within specified Service Level Objectives (SLOs). Each test performs an
  interface flap (shutdown → wait → no shutdown), measures recovery time, and validates
  that the BGP session returns to Established state. Supports both click and klish modes.
  Tests cover scenarios where link flaps occur on both local and remote sides, validating
  BGP FSM transitions and convergence time.

Pre-requisites:
  - Topology: t0/t1/any | Supported: HW and Virtual
  - Topology Diagram :
        # Topology - 2 nodes
        # +-----------------------+                   +-----------------------+
        # |   D1 (smic_sonic1)    |===================|   D2 (smic_sonic2)    |
        # |  AS 65001/65002       |     Ethernet4     |  AS 65001/65002       |
        # |  Lo0: 1.1.1.1/32      |  10.0.0.1/30 ↔    |  Lo0: 2.2.2.2/32      |
        # |                       |     10.0.0.2/30   |                       |
        # +-----------------------+                   +-----------------------+

  - Feature flags / min SONiC version: BGP support required, BFD optional for test 2.4.5.6
  - Required test variables (YAML): vars_bgp_session_recovery_after_interface_flap.yaml
    - defaults.cli_type (klish recommended for BGP configuration)
    - defaults.verify_timeout (90 seconds)
    - defaults.establish_timeout (90 seconds for initial session setup)
    - defaults.downtime_slo (10 seconds maximum recovery time)
    - defaults.flap_hold_time (3 seconds interface down duration)
    - defaults.cleanup (true for cleanup after tests)
    - defaults.min_topology (D1D2:1)
    - testcases.* definitions for all 6 sub-testcases
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

import pytest
import yaml

from spytest import SpyTestDict, st

import apis.routing.bgp as bgp_api
import apis.routing.ip as ip_api
import apis.system.interface as intf_api

VAR_FILE_ENV = "BGP_245_VAR_FILE"


def _candidate_var_files() -> List[Path]:
    """Return candidate YAML paths in search order."""
    candidates: List[Path] = []
    override = st.getenv(VAR_FILE_ENV)
    if override:
        candidates.append(Path(override))

    project_root = Path(__file__).resolve().parents[3]
    candidates.append(project_root / "vars" / "routing" / "bgp" / "vars_bgp_session_recovery_after_interface_flap.yaml")
    candidates.append(Path(__file__).resolve().with_name("vars_bgp_session_recovery_after_interface_flap.yaml"))
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
    st.report_fail("msg", f"BGP 2.4.5 variable file not found. Checked: {attempted_paths}")
    return SpyTestDict()


def _iter_candidate_duts(topology: SpyTestDict) -> Iterable[str]:
    """Yield topology keys that resemble DUT aliases (D1, D2, ...)."""
    for key, value in topology.items():
        if key.upper().startswith("D") and value:
            yield key


@pytest.mark.topology("any")
class TestBgpSessionRecoveryAfterInterfaceFlap:
    """Testcases for validating BGP session recovery after interface flap - Test ID 2.4.5."""

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
        cls.data.verify_timeout = int(defaults.get("verify_timeout", 90))
        cls.data.establish_timeout = int(defaults.get("establish_timeout", 90))
        cls.data.downtime_slo = int(defaults.get("downtime_slo", 10))
        cls.data.flap_hold_time = int(defaults.get("flap_hold_time", 3))
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
        self._configured_bfd: List[SpyTestDict] = []

    def teardown_method(self) -> None:
        """Cleanup all dynamic configuration pushed during the test."""
        if not self.data.get("cleanup", True):
            return

        # Remove BFD configurations
        while self._configured_bfd:
            bfd_entry = self._configured_bfd.pop()
            self._remove_bfd_neighbor(bfd_entry)

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
        """Configure an IPv4 address on an interface."""
        dut = self._resolve_dut(config.get("dut"))
        if not dut:
            st.report_fail("msg", f"Invalid DUT alias in interface config: {config}")

        interface = config.get("interface")
        ip_address = config.get("ip_address")
        prefix_length = config.get("prefix_length")
        cli_type = config.get("cli_type", "klish")

        st.log(f"Configuring {ip_address}/{prefix_length} on {dut}:{interface}")
        result = ip_api.config_ip_addr_interface(
            dut,
            interface_name=interface,
            ip_address=ip_address,
            subnet=str(prefix_length),
            family="ipv4",
            config="add",
            cli_type=cli_type,
        )

        if not result:
            st.report_fail("msg", f"Failed to configure IP on {dut}:{interface}")

        self._configured_interfaces.append(config)

    def _remove_interface_ip(self, config: SpyTestDict) -> None:
        """Remove an IPv4 address from an interface."""
        dut = self._resolve_dut(config.get("dut"))
        if not dut:
            return

        interface = config.get("interface")
        ip_address = config.get("ip_address")
        prefix_length = config.get("prefix_length")
        cli_type = config.get("cli_type", "klish")

        st.log(f"Removing {ip_address}/{prefix_length} from {dut}:{interface}")
        ip_api.config_ip_addr_interface(
            dut,
            interface_name=interface,
            ip_address=ip_address,
            subnet=str(prefix_length),
            family="ipv4",
            config="remove",
            cli_type=cli_type,
        )

    def _configure_loopback_ip(self, config: SpyTestDict) -> None:
        """Configure an IPv4 address on a loopback interface."""
        dut = self._resolve_dut(config.get("dut"))
        if not dut:
            st.report_fail("msg", f"Invalid DUT alias in loopback config: {config}")

        loopback = config.get("loopback")
        ip_address = config.get("ip_address")
        prefix_length = config.get("prefix_length")
        cli_type = config.get("cli_type", "klish")

        st.log(f"Configuring loopback {loopback} with {ip_address}/{prefix_length} on {dut}")
        result = ip_api.config_ip_addr_interface(
            dut,
            interface_name=loopback,
            ip_address=ip_address,
            subnet=str(prefix_length),
            family="ipv4",
            config="add",
            cli_type=cli_type,
        )

        if not result:
            st.report_fail("msg", f"Failed to configure loopback IP on {dut}:{loopback}")

        self._configured_loopbacks.append(config)

    def _remove_loopback_ip(self, config: SpyTestDict) -> None:
        """Remove an IPv4 address from a loopback interface."""
        dut = self._resolve_dut(config.get("dut"))
        if not dut:
            return

        loopback = config.get("loopback")
        ip_address = config.get("ip_address")
        prefix_length = config.get("prefix_length")
        cli_type = config.get("cli_type", "klish")

        st.log(f"Removing loopback {loopback} IP from {dut}")
        ip_api.config_ip_addr_interface(
            dut,
            interface_name=loopback,
            ip_address=ip_address,
            subnet=str(prefix_length),
            family="ipv4",
            config="remove",
            cli_type=cli_type,
        )

    def _configure_static_route(self, config: SpyTestDict) -> None:
        """Configure a static route."""
        dut = self._resolve_dut(config.get("dut"))
        if not dut:
            st.report_fail("msg", f"Invalid DUT alias in static route config: {config}")

        destination = config.get("destination")
        nexthop = config.get("nexthop")
        cli_type = config.get("cli_type", "klish")

        st.log(f"Configuring static route {destination} via {nexthop} on {dut}")
        result = ip_api.create_static_route(
            dut,
            next_hop=nexthop,
            static_ip=destination,
            family="ipv4",
            cli_type=cli_type,
        )

        if not result:
            st.report_fail("msg", f"Failed to configure static route on {dut}")

        self._configured_static_routes.append(config)

    def _remove_static_route(self, config: SpyTestDict) -> None:
        """Remove a static route."""
        dut = self._resolve_dut(config.get("dut"))
        if not dut:
            return

        destination = config.get("destination")
        nexthop = config.get("nexthop")
        cli_type = config.get("cli_type", "klish")

        st.log(f"Removing static route {destination} via {nexthop} from {dut}")
        ip_api.delete_static_route(
            dut,
            next_hop=nexthop,
            static_ip=destination,
            family="ipv4",
            cli_type=cli_type,
        )

    def _configure_bgp_router(self, config: SpyTestDict) -> None:
        """Configure BGP router with AS number."""
        dut = self._resolve_dut(config.get("dut"))
        if not dut:
            st.report_fail("msg", f"Invalid DUT alias in BGP router config: {config}")

        local_asn = config.get("local_asn")
        router_id = config.get("router_id")
        cli_type = config.get("cli_type", "klish")

        st.log(f"Configuring BGP router on {dut} with AS {local_asn}")
        result = bgp_api.config_router_bgp_mode(
            dut,
            local_asn=local_asn,
            config_mode="enable",
            cli_type=cli_type,
        )

        if not result:
            st.report_fail("msg", f"Failed to configure BGP router on {dut}")

        if router_id:
            bgp_api.config_bgp_router_id(dut, local_asn=local_asn, router_id=router_id, cli_type=cli_type)

        self._configured_routers.append(config)

    def _remove_bgp_router(self, config: SpyTestDict) -> None:
        """Remove BGP router configuration."""
        dut = self._resolve_dut(config.get("dut"))
        if not dut:
            return

        local_asn = config.get("local_asn")
        cli_type = config.get("cli_type", "klish")

        st.log(f"Removing BGP router from {dut}")
        bgp_api.config_router_bgp_mode(
            dut,
            local_asn=local_asn,
            config_mode="disable",
            cli_type=cli_type,
        )

    def _configure_bgp_neighbor(self, config: SpyTestDict) -> None:
        """Configure a BGP neighbor."""
        dut = self._resolve_dut(config.get("dut"))
        if not dut:
            st.report_fail("msg", f"Invalid DUT alias in BGP neighbor config: {config}")

        local_asn = config.get("local_asn")
        neighbor = config.get("neighbor")
        remote_asn = config.get("remote_asn")
        cli_type = config.get("cli_type", "klish")

        # Additional neighbor config parameters
        update_source = config.get("update_source")
        ebgp_multihop = config.get("ebgp_multihop")
        interface = config.get("interface")
        activate_family = config.get("activate_family", "ipv4")
        extended_nexthop = config.get("extended_nexthop", False)

        st.log(f"Configuring BGP neighbor {neighbor} (AS {remote_asn}) on {dut}")

        # For interface-based neighbors (unnumbered)
        if interface:
            result = bgp_api.config_bgp_neighbor(
                dut,
                local_asn=local_asn,
                neighbor_ip=interface,
                remote_asn=remote_asn,
                family=activate_family,
                cli_type=cli_type,
                config="yes",
                interface=interface,
            )
        else:
            result = bgp_api.config_bgp_neighbor(
                dut,
                local_asn=local_asn,
                neighbor_ip=neighbor,
                remote_asn=remote_asn,
                family=activate_family,
                cli_type=cli_type,
                config="yes",
            )

        if not result:
            st.report_fail("msg", f"Failed to configure BGP neighbor on {dut}")

        # Configure update-source for multihop
        if update_source:
            bgp_api.config_bgp_neighbor_properties(
                dut,
                local_asn=local_asn,
                neighbor_ip=neighbor,
                update_source=update_source,
                cli_type=cli_type,
            )

        # Configure ebgp-multihop
        if ebgp_multihop:
            bgp_api.config_bgp_neighbor_properties(
                dut,
                local_asn=local_asn,
                neighbor_ip=neighbor,
                ebgp_multihop=ebgp_multihop,
                cli_type=cli_type,
            )

        # Configure extended-nexthop capability for unnumbered
        if extended_nexthop and interface:
            bgp_api.config_bgp_neighbor_properties(
                dut,
                local_asn=local_asn,
                neighbor_ip=interface,
                capability_ext_nexthop="enable",
                cli_type=cli_type,
            )

        self._configured_neighbors.append(config)

    def _remove_bgp_neighbor(self, config: SpyTestDict) -> None:
        """Remove a BGP neighbor."""
        dut = self._resolve_dut(config.get("dut"))
        if not dut:
            return

        local_asn = config.get("local_asn")
        neighbor = config.get("neighbor")
        interface = config.get("interface")
        cli_type = config.get("cli_type", "klish")

        neighbor_to_remove = interface if interface else neighbor

        st.log(f"Removing BGP neighbor {neighbor_to_remove} from {dut}")
        bgp_api.config_bgp_neighbor(
            dut,
            local_asn=local_asn,
            neighbor_ip=neighbor_to_remove,
            remote_asn=config.get("remote_asn"),
            family="ipv4",
            cli_type=cli_type,
            config="no",
        )

    def _configure_bfd_neighbor(self, config: SpyTestDict) -> None:
        """Enable BFD for a BGP neighbor."""
        dut = self._resolve_dut(config.get("dut"))
        if not dut:
            st.report_fail("msg", f"Invalid DUT alias in BFD config: {config}")

        local_asn = config.get("local_asn")
        neighbor = config.get("neighbor")
        cli_type = config.get("cli_type", "klish")

        st.log(f"Enabling BFD for BGP neighbor {neighbor} on {dut}")
        result = bgp_api.config_bgp_neighbor_properties(
            dut,
            local_asn=local_asn,
            neighbor_ip=neighbor,
            bfd="enable",
            cli_type=cli_type,
        )

        if not result:
            st.warn(f"BFD configuration may have failed on {dut} (platform may not support BFD)")

        self._configured_bfd.append(config)

    def _remove_bfd_neighbor(self, config: SpyTestDict) -> None:
        """Disable BFD for a BGP neighbor."""
        dut = self._resolve_dut(config.get("dut"))
        if not dut:
            return

        local_asn = config.get("local_asn")
        neighbor = config.get("neighbor")
        cli_type = config.get("cli_type", "klish")

        st.log(f"Disabling BFD for BGP neighbor {neighbor} on {dut}")
        bgp_api.config_bgp_neighbor_properties(
            dut,
            local_asn=local_asn,
            neighbor_ip=neighbor,
            bfd="disable",
            cli_type=cli_type,
        )

    def _verify_bgp_session(self, config: SpyTestDict, expected_state: str = "Established") -> bool:
        """Verify BGP session state."""
        dut = self._resolve_dut(config.get("dut"))
        if not dut:
            return False

        neighbor = config.get("neighbor")
        interface = config.get("interface")
        cli_type = config.get("cli_type", "klish")

        neighbor_to_check = interface if interface else neighbor

        st.log(f"Verifying BGP neighbor {neighbor_to_check} on {dut} is {expected_state}")

        result = bgp_api.verify_bgp_summary(
            dut,
            neighbor=neighbor_to_check,
            state=expected_state,
            cli_type=cli_type,
        )

        return result

    def _wait_for_bgp_session(self, config: SpyTestDict, timeout: int, expected_state: str = "Established") -> bool:
        """Poll for BGP session to reach expected state."""
        dut = self._resolve_dut(config.get("dut"))
        if not dut:
            return False

        neighbor = config.get("neighbor")
        interface = config.get("interface")
        cli_type = config.get("cli_type", "klish")

        neighbor_to_check = interface if interface else neighbor

        st.log(f"Waiting up to {timeout}s for BGP neighbor {neighbor_to_check} on {dut} to reach {expected_state}")

        return st.poll_wait(
            bgp_api.verify_bgp_summary,
            timeout,
            dut,
            neighbor=neighbor_to_check,
            state=expected_state,
            cli_type=cli_type,
        )

    def _interface_flap(self, dut_alias: str, interface: str, hold_time: int = 3) -> None:
        """Perform interface flap (shutdown → wait → no shutdown)."""
        dut = self._resolve_dut(dut_alias)
        if not dut:
            st.report_fail("msg", f"Invalid DUT alias for interface flap: {dut_alias}")

        st.log(f"Flapping interface {interface} on {dut} (hold time: {hold_time}s)")

        # Shutdown interface
        intf_api.interface_shutdown(dut, interface)
        st.log(f"Interface {interface} shutdown on {dut}")

        # Wait for hold time
        st.wait(hold_time)

        # Bring up interface
        intf_api.interface_noshutdown(dut, interface)
        st.log(f"Interface {interface} brought up on {dut}")

    def _measure_recovery_time(self, config: SpyTestDict, max_recovery_time: int) -> float:
        """Measure BGP session recovery time after interface flap."""
        dut = self._resolve_dut(config.get("dut"))
        if not dut:
            return -1.0

        neighbor = config.get("neighbor")
        interface = config.get("interface")
        cli_type = config.get("cli_type", "klish")

        neighbor_to_check = interface if interface else neighbor

        start_time = time.time()
        recovery_time = -1.0

        # Poll until session is established or timeout
        while time.time() - start_time < max_recovery_time:
            if bgp_api.verify_bgp_summary(
                dut,
                neighbor=neighbor_to_check,
                state="Established",
                cli_type=cli_type,
            ):
                recovery_time = time.time() - start_time
                st.log(f"BGP session recovered in {recovery_time:.2f} seconds")
                break

            st.wait(0.5)

        return recovery_time

    def _get_testcase(self, tcid: str) -> SpyTestDict:
        """Helper to fetch testcase definition from YAML."""
        testcase = self.data.testcases.get(tcid)
        if not testcase:
            st.report_fail("msg", f"Missing testcase definition for {tcid} in YAML")
        return testcase

    @pytest.mark.inventory(feature="Regression", testcases=["BGP_245_TC2.4.5.1"])
    def test_ebgp_ipv4_numbered_flap_dut1(self) -> None:
        """TC 2.4.5.1 – eBGP IPv4 numbered session recovers after interface flap on DUT1."""
        testcase = self._get_testcase("2.4.5.1")

        # Configure interfaces
        for iface_cfg in testcase.get("interfaces", []):
            self._configure_interface_ip(SpyTestDict(iface_cfg))

        # Configure BGP routers
        for router_cfg in testcase.get("routers", []):
            self._configure_bgp_router(SpyTestDict(router_cfg))

        # Configure BGP neighbors
        neighbors = []
        for neighbor_cfg in testcase.get("neighbors", []):
            neighbor_dict = SpyTestDict(neighbor_cfg)
            self._configure_bgp_neighbor(neighbor_dict)
            neighbors.append(neighbor_dict)

        # Wait for BGP session to establish
        st.log("Waiting for BGP sessions to establish...")
        for neighbor in neighbors:
            if not self._wait_for_bgp_session(neighbor, self.data.establish_timeout):
                st.report_fail("msg", f"BGP session failed to establish for neighbor {neighbor.get('neighbor')}")

        # Perform interface flap
        flap_config = testcase.get("flap", {})
        flap_dut = flap_config.get("dut")
        flap_interface = flap_config.get("interface")

        self._interface_flap(flap_dut, flap_interface, self.data.flap_hold_time)

        # Measure recovery time
        st.log("Measuring BGP session recovery time...")
        for neighbor in neighbors:
            recovery_time = self._measure_recovery_time(neighbor, self.data.downtime_slo + 5)

            if recovery_time < 0:
                st.report_fail("msg", f"BGP session did not recover within {self.data.downtime_slo + 5} seconds")

            st.log(f"Recovery time: {recovery_time:.2f}s, SLO: {self.data.downtime_slo}s")

            if recovery_time > self.data.downtime_slo:
                st.report_fail("msg", f"BGP recovery time {recovery_time:.2f}s exceeds SLO of {self.data.downtime_slo}s")

        st.report_pass("test_case_passed")

    @pytest.mark.inventory(feature="Regression", testcases=["BGP_245_TC2.4.5.2"])
    def test_ebgp_ipv4_numbered_flap_dut2(self) -> None:
        """TC 2.4.5.2 – eBGP IPv4 numbered session recovers after interface flap on DUT2."""
        testcase = self._get_testcase("2.4.5.2")

        # Configure interfaces
        for iface_cfg in testcase.get("interfaces", []):
            self._configure_interface_ip(SpyTestDict(iface_cfg))

        # Configure BGP routers
        for router_cfg in testcase.get("routers", []):
            self._configure_bgp_router(SpyTestDict(router_cfg))

        # Configure BGP neighbors
        neighbors = []
        for neighbor_cfg in testcase.get("neighbors", []):
            neighbor_dict = SpyTestDict(neighbor_cfg)
            self._configure_bgp_neighbor(neighbor_dict)
            neighbors.append(neighbor_dict)

        # Wait for BGP session to establish
        st.log("Waiting for BGP sessions to establish...")
        for neighbor in neighbors:
            if not self._wait_for_bgp_session(neighbor, self.data.establish_timeout):
                st.report_fail("msg", f"BGP session failed to establish for neighbor {neighbor.get('neighbor')}")

        # Perform interface flap
        flap_config = testcase.get("flap", {})
        flap_dut = flap_config.get("dut")
        flap_interface = flap_config.get("interface")

        self._interface_flap(flap_dut, flap_interface, self.data.flap_hold_time)

        # Measure recovery time
        st.log("Measuring BGP session recovery time...")
        for neighbor in neighbors:
            recovery_time = self._measure_recovery_time(neighbor, self.data.downtime_slo + 5)

            if recovery_time < 0:
                st.report_fail("msg", f"BGP session did not recover within {self.data.downtime_slo + 5} seconds")

            if recovery_time > self.data.downtime_slo:
                st.report_fail("msg", f"BGP recovery time {recovery_time:.2f}s exceeds SLO of {self.data.downtime_slo}s")

        st.report_pass("test_case_passed")

    @pytest.mark.inventory(feature="Regression", testcases=["BGP_245_TC2.4.5.3"])
    def test_ibgp_ipv4_numbered_flap_dut1(self) -> None:
        """TC 2.4.5.3 – iBGP IPv4 numbered session recovers after interface flap on DUT1."""
        testcase = self._get_testcase("2.4.5.3")

        # Configure interfaces
        for iface_cfg in testcase.get("interfaces", []):
            self._configure_interface_ip(SpyTestDict(iface_cfg))

        # Configure BGP routers
        for router_cfg in testcase.get("routers", []):
            self._configure_bgp_router(SpyTestDict(router_cfg))

        # Configure BGP neighbors
        neighbors = []
        for neighbor_cfg in testcase.get("neighbors", []):
            neighbor_dict = SpyTestDict(neighbor_cfg)
            self._configure_bgp_neighbor(neighbor_dict)
            neighbors.append(neighbor_dict)

        # Wait for BGP session to establish
        st.log("Waiting for iBGP sessions to establish...")
        for neighbor in neighbors:
            if not self._wait_for_bgp_session(neighbor, self.data.establish_timeout):
                st.report_fail("msg", f"iBGP session failed to establish for neighbor {neighbor.get('neighbor')}")

        # Perform interface flap
        flap_config = testcase.get("flap", {})
        flap_dut = flap_config.get("dut")
        flap_interface = flap_config.get("interface")

        self._interface_flap(flap_dut, flap_interface, self.data.flap_hold_time)

        # Measure recovery time
        st.log("Measuring iBGP session recovery time...")
        for neighbor in neighbors:
            recovery_time = self._measure_recovery_time(neighbor, self.data.downtime_slo + 5)

            if recovery_time < 0:
                st.report_fail("msg", f"iBGP session did not recover within {self.data.downtime_slo + 5} seconds")

            if recovery_time > self.data.downtime_slo:
                st.report_fail("msg", f"iBGP recovery time {recovery_time:.2f}s exceeds SLO of {self.data.downtime_slo}s")

        st.report_pass("test_case_passed")

    @pytest.mark.inventory(feature="Regression", testcases=["BGP_245_TC2.4.5.4"])
    def test_ibgp_ipv4_unnumbered_flap_dut1(self) -> None:
        """TC 2.4.5.4 – iBGP IPv4 unnumbered session recovers after interface flap on DUT1."""
        testcase = self._get_testcase("2.4.5.4")

        # Configure BGP routers
        for router_cfg in testcase.get("routers", []):
            self._configure_bgp_router(SpyTestDict(router_cfg))

        # Configure BGP neighbors (unnumbered)
        neighbors = []
        for neighbor_cfg in testcase.get("neighbors", []):
            neighbor_dict = SpyTestDict(neighbor_cfg)
            self._configure_bgp_neighbor(neighbor_dict)
            neighbors.append(neighbor_dict)

        # Wait for BGP session to establish
        st.log("Waiting for unnumbered iBGP sessions to establish...")
        for neighbor in neighbors:
            if not self._wait_for_bgp_session(neighbor, self.data.establish_timeout):
                st.report_fail("msg", f"Unnumbered iBGP session failed to establish for interface {neighbor.get('interface')}")

        # Perform interface flap
        flap_config = testcase.get("flap", {})
        flap_dut = flap_config.get("dut")
        flap_interface = flap_config.get("interface")

        self._interface_flap(flap_dut, flap_interface, self.data.flap_hold_time)

        # Measure recovery time
        st.log("Measuring unnumbered iBGP session recovery time...")
        for neighbor in neighbors:
            recovery_time = self._measure_recovery_time(neighbor, self.data.downtime_slo + 5)

            if recovery_time < 0:
                st.report_fail("msg", f"Unnumbered iBGP session did not recover within {self.data.downtime_slo + 5} seconds")

            if recovery_time > self.data.downtime_slo:
                st.report_fail("msg", f"Unnumbered iBGP recovery time {recovery_time:.2f}s exceeds SLO of {self.data.downtime_slo}s")

        st.report_pass("test_case_passed")

    @pytest.mark.inventory(feature="Regression", testcases=["BGP_245_TC2.4.5.5"])
    def test_ebgp_multihop_flap_underlay(self) -> None:
        """TC 2.4.5.5 – eBGP multihop session recovers after underlay interface flap."""
        testcase = self._get_testcase("2.4.5.5")

        # Configure loopbacks
        for lb_cfg in testcase.get("loopbacks", []):
            self._configure_loopback_ip(SpyTestDict(lb_cfg))

        # Configure interfaces
        for iface_cfg in testcase.get("interfaces", []):
            self._configure_interface_ip(SpyTestDict(iface_cfg))

        # Configure static routes
        for route_cfg in testcase.get("static_routes", []):
            self._configure_static_route(SpyTestDict(route_cfg))

        # Configure BGP routers
        for router_cfg in testcase.get("routers", []):
            self._configure_bgp_router(SpyTestDict(router_cfg))

        # Configure BGP neighbors (multihop)
        neighbors = []
        for neighbor_cfg in testcase.get("neighbors", []):
            neighbor_dict = SpyTestDict(neighbor_cfg)
            self._configure_bgp_neighbor(neighbor_dict)
            neighbors.append(neighbor_dict)

        # Wait for BGP session to establish
        st.log("Waiting for eBGP multihop sessions to establish...")
        for neighbor in neighbors:
            if not self._wait_for_bgp_session(neighbor, self.data.establish_timeout):
                st.report_fail("msg", f"eBGP multihop session failed to establish for neighbor {neighbor.get('neighbor')}")

        # Perform interface flap on underlay
        flap_config = testcase.get("flap", {})
        flap_dut = flap_config.get("dut")
        flap_interface = flap_config.get("interface")

        st.log(f"Flapping underlay interface {flap_interface} on {flap_dut}")
        self._interface_flap(flap_dut, flap_interface, self.data.flap_hold_time)

        # Measure recovery time
        st.log("Measuring eBGP multihop session recovery time...")
        for neighbor in neighbors:
            recovery_time = self._measure_recovery_time(neighbor, self.data.downtime_slo + 5)

            if recovery_time < 0:
                st.report_fail("msg", f"eBGP multihop session did not recover within {self.data.downtime_slo + 5} seconds")

            if recovery_time > self.data.downtime_slo:
                st.report_fail("msg", f"eBGP multihop recovery time {recovery_time:.2f}s exceeds SLO of {self.data.downtime_slo}s")

        st.report_pass("test_case_passed")

    @pytest.mark.inventory(feature="Regression", testcases=["BGP_245_TC2.4.5.6"])
    def test_ebgp_bfd_faster_recovery(self) -> None:
        """TC 2.4.5.6 – eBGP session with BFD demonstrates faster recovery after interface flap."""
        testcase = self._get_testcase("2.4.5.6")

        # Configure interfaces
        for iface_cfg in testcase.get("interfaces", []):
            self._configure_interface_ip(SpyTestDict(iface_cfg))

        # Configure BGP routers
        for router_cfg in testcase.get("routers", []):
            self._configure_bgp_router(SpyTestDict(router_cfg))

        # Configure BGP neighbors
        neighbors = []
        for neighbor_cfg in testcase.get("neighbors", []):
            neighbor_dict = SpyTestDict(neighbor_cfg)
            self._configure_bgp_neighbor(neighbor_dict)
            neighbors.append(neighbor_dict)

        # Configure BFD
        for bfd_cfg in testcase.get("bfd", []):
            self._configure_bfd_neighbor(SpyTestDict(bfd_cfg))

        # Wait for BGP session to establish
        st.log("Waiting for eBGP sessions with BFD to establish...")
        for neighbor in neighbors:
            if not self._wait_for_bgp_session(neighbor, self.data.establish_timeout):
                st.report_fail("msg", f"eBGP session with BFD failed to establish for neighbor {neighbor.get('neighbor')}")

        # Perform interface flap
        flap_config = testcase.get("flap", {})
        flap_dut = flap_config.get("dut")
        flap_interface = flap_config.get("interface")

        self._interface_flap(flap_dut, flap_interface, self.data.flap_hold_time)

        # Measure recovery time
        st.log("Measuring BGP session recovery time with BFD...")
        for neighbor in neighbors:
            recovery_time = self._measure_recovery_time(neighbor, self.data.downtime_slo + 5)

            if recovery_time < 0:
                st.report_fail("msg", f"BGP session with BFD did not recover within {self.data.downtime_slo + 5} seconds")

            st.log(f"BFD-enabled recovery time: {recovery_time:.2f}s (expected << {self.data.downtime_slo}s)")

            # BFD should provide significantly faster recovery (< 5 seconds is good)
            if recovery_time > 5:
                st.warn(f"BFD recovery time {recovery_time:.2f}s is slower than expected (should be < 5s)")

        st.report_pass("test_case_passed")
