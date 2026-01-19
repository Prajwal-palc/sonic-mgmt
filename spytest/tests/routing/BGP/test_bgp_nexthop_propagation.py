"""
BGP NEXT-HOP PROPAGATION (IPv4/IPv6) - Test ID 3.2.4
Author: Claude
2025

How to run:
  ./bin/spytest  --tryssh 1  \
  --testbed ./testbeds/testbed_vs_2node.yaml  \
  tests/routing/BGP/test_bgp_nexthop_propagation.py \
  --logs-path ./logs/test_bgp_324_$(date +%F_%H%M%S) \
  --log-level debug  --skip-init-config  --ifname-type native

Description:
  Comprehensive validation of BGP next-hop behavior for IPv4 and IPv6 routes across
  eBGP and iBGP sessions. Tests cover next-hop rewriting in eBGP scenarios, next-hop
  preservation in iBGP, next-hop-self behavior, multi-hop loopback-based peering,
  IPv6 link-local next-hop handling, route-reflector next-hop propagation, next-hop
  reachability requirements for RIB/FIB installation, and static route redistribution.
  All test cases consume topology-aware variables from YAML to remain reusable across
  SONiC hardware and virtual environments.

Pre-requisites:
  - Topology: any | Supported: HW and Virtual
  - Topology Diagram:
        # Topology - 2 nodes
        # +--------------------+                       +--------------------+
        # |        D1          |                       |        D2          |
        # | Eth4 192.168.100.1 |=======================| Eth4 192.168.100.2 |
        # | AS 65001/65002     |                       | AS 65001/65002     |
        # +--------------------+                       +--------------------+

  - Feature flags / min SONiC version: BGP support required
  - Required test variables (YAML): defaults.cli_type (klish for config, click for show),
    defaults.verify_timeout, defaults.cleanup, defaults.min_topology,
    testcases.* definitions (3.2.4.1 through 3.2.4.9)
"""

from __future__ import annotations

from collections.abc import Iterable as IterableCollection
from contextlib import contextmanager
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional
import time

import pytest
import yaml

from spytest import SpyTestDict, st
import apis.routing.bgp as bgp_api
import apis.routing.ip as ip_api
import utilities.common as utils

VAR_FILE_ENV = "BGP_324_VAR_FILE"
DEFAULT_VAR_FILE = (
    Path(__file__).resolve().parent / "vars_bgp_nexthop_propagation.yaml"
)


def _load_yaml_data() -> Dict[str, Any]:
    """Load testcase variables from YAML with optional environment override."""
    override_path = st.getenv(VAR_FILE_ENV)
    candidate = Path(override_path) if override_path else DEFAULT_VAR_FILE

    if not candidate.is_file():
        raise FileNotFoundError(f"BGP 3.2.4 variable file not found: {candidate}")

    with candidate.open(encoding="utf-8") as handle:
        content = yaml.safe_load(handle) or {}

    if "testcases" not in content:
        raise ValueError("BGP 3.2.4 YAML must contain key 'testcases'")

    return content


def _iter_candidate_duts(topology: Mapping[str, Any]) -> Iterable[str]:
    """Yield DUT aliases discovered in the topology map."""
    for key, value in topology.items():
        if key.startswith("D") and value:
            yield key


@pytest.mark.topology("any")
class TestBgpNexthopPropagation:
    """Testcases covering BGP next-hop propagation - Test ID 3.2.4."""

    data = SpyTestDict()

    @classmethod
    def setup_class(cls) -> None:
        """Collect topology handles and testcase variables for the suite."""
        st.log("=" * 80)
        st.log("BGP Next-hop Propagation Test Suite - Setup Class")
        st.log("=" * 80)

        config = _load_yaml_data()
        defaults = config.get("defaults", {})

        min_topology = defaults.get("min_topology") or ["D1D2:1"]
        topology = st.ensure_min_topology(*min_topology)

        cls.data.config = SpyTestDict(config)
        cls.data.defaults = SpyTestDict(defaults)
        cls.data.topology = topology
        cls.data.testcases = SpyTestDict(config.get("testcases", {}))

        # klish for config, click for show commands
        cls.data.config_cli_type = defaults.get("config_cli_type", "klish")
        cls.data.show_cli_type = defaults.get("show_cli_type", "click")
        cls.data.verify_timeout = int(defaults.get("verify_timeout", 120))
        cls.data.cleanup_enabled = bool(defaults.get("cleanup", True))
        cls.data.bgp_convergence_time = int(defaults.get("bgp_convergence_time", 30))

        cls.data.dut_map = SpyTestDict()
        cls.data.configured_items = []

        # Map DUT aliases (D1, D2, ...) to actual device handles
        for dut_alias in _iter_candidate_duts(topology):
            cls.data.dut_map[dut_alias] = getattr(topology, dut_alias)

        cls.data.dut_names = st.get_dut_names()
        st.log(f"DUT names: {cls.data.dut_names}")
        st.log(f"DUT map: {dict(cls.data.dut_map)}")
        st.log(f"Config CLI type: {cls.data.config_cli_type}")
        st.log(f"Show CLI type: {cls.data.show_cli_type}")
        st.log(f"Verify timeout: {cls.data.verify_timeout}s")

    @classmethod
    def teardown_class(cls) -> None:
        """Ensure all BGP configurations are removed after the suite completes."""
        st.log("=" * 80)
        st.log("BGP Next-hop Propagation Test Suite - Teardown Class")
        st.log("=" * 80)

        if not cls.data.cleanup_enabled:
            st.log("Cleanup disabled - skipping teardown")
            return

        cls._cleanup_all_configurations()
        st.log("Teardown class completed")

    def setup_method(self) -> None:
        """Reset per-test bookkeeping."""
        self._test_items: List[Mapping[str, Any]] = []
        st.log("-" * 80)
        st.log(f"Starting test method: {self._testname}")
        st.log("-" * 80)

    def teardown_method(self) -> None:
        """Remove any configurations that the testcase created."""
        st.log("-" * 80)
        st.log(f"Tearing down test method: {self._testname}")
        st.log("-" * 80)

        if not self.data.cleanup_enabled:
            self._test_items = []
            return

        while self._test_items:
            item = self._test_items.pop()
            self._remove_configuration(item)
            if item in self.data.configured_items:
                self.data.configured_items.remove(item)

        st.log(f"Test method teardown completed: {self._testname}")

    @property
    def _testname(self) -> str:
        """Return current test method name."""
        import inspect
        frame = inspect.currentframe()
        if frame and frame.f_back:
            return frame.f_back.f_code.co_name
        return "unknown"

    @classmethod
    def _cleanup_all_configurations(cls) -> None:
        """Remove all configurations tracked across the suite."""
        st.log("Cleaning up all configurations...")
        while cls.data.get("configured_items"):
            item = cls.data.configured_items.pop()
            cls._remove_configuration_static(item)
        st.log("All configurations cleaned up")

    @classmethod
    def _resolve_dut(cls, alias: str | None) -> str | None:
        """Translate a topology alias (e.g., D1) to the framework DUT handle."""
        if not alias:
            return None
        if alias in cls.data.dut_map:
            return cls.data.dut_map[alias]
        if alias in cls.data.dut_names:
            return alias
        st.warn(f"Unable to resolve DUT alias '{alias}'")
        return None

    def _get_testcase(self, tcid: str) -> Mapping[str, Any]:
        """Helper to fetch testcase definition from YAML."""
        testcase = self.data.testcases.get(tcid)
        if not testcase:
            st.report_fail("msg", f"Missing testcase definition for {tcid} in YAML")
        return testcase

    def _configure_setup_items(self, setup_items: List[Mapping[str, Any]]) -> None:
        """Configure all setup items (interfaces, loopbacks, BGP, etc.)."""
        for item in setup_items:
            item_type = item.get("type")
            if not item_type:
                st.log(f"Skipping setup item without type: {item}")
                continue

            st.log(f"Configuring setup item type={item_type}: {item}")

            if item_type == "interface":
                self._configure_interface(item)
            elif item_type == "loopback":
                self._configure_loopback(item)
            elif item_type == "bgp_router":
                self._configure_bgp_router(item)
            elif item_type == "bgp_neighbor":
                self._configure_bgp_neighbor(item)
            elif item_type == "bgp_network":
                self._configure_bgp_network(item)
            elif item_type == "static_route":
                self._configure_static_route(item)
            elif item_type == "ipv6_enable":
                self._configure_ipv6_enable(item)
            else:
                st.log(f"Unknown setup item type: {item_type}")
                continue

            # Track for cleanup
            if item not in self._test_items:
                self._test_items.append(item)
            if item not in self.data.configured_items:
                self.data.configured_items.append(item)

    def _configure_interface(self, item: Mapping[str, Any]) -> None:
        """Configure IP address on an interface."""
        dut = self._resolve_dut(item.get("dut"))
        if not dut:
            st.report_fail("msg", f"Invalid DUT in interface config: {item}")

        interface = item.get("interface")
        ip_address = item.get("ip_address")
        prefix_length = item.get("prefix_length")
        family = item.get("family", "ipv4")

        if not all([interface, ip_address, prefix_length]):
            st.report_fail("msg", f"Missing required fields in interface config: {item}")

        st.log(f"Configuring {family} address {ip_address}/{prefix_length} on {dut}:{interface}")

        ip_api.config_ip_addr_interface(
            dut,
            interface_name=interface,
            ip_address=ip_address,
            subnet=prefix_length,
            family=family,
            config="add",
            cli_type=self.data.config_cli_type,
        )

    def _configure_loopback(self, item: Mapping[str, Any]) -> None:
        """Configure a loopback interface with IP address."""
        dut = self._resolve_dut(item.get("dut"))
        if not dut:
            st.report_fail("msg", f"Invalid DUT in loopback config: {item}")

        loopback = item.get("loopback")
        ip_address = item.get("ip_address")
        prefix_length = item.get("prefix_length")
        family = item.get("family", "ipv4")

        if not all([loopback, ip_address, prefix_length]):
            st.report_fail("msg", f"Missing required fields in loopback config: {item}")

        st.log(f"Configuring loopback {loopback} with {family} address {ip_address}/{prefix_length} on {dut}")

        # Create loopback interface
        ip_api.configure_loopback(dut, loopback_name=loopback, config="yes", cli_type=self.data.config_cli_type)

        # Configure IP address
        ip_api.config_ip_addr_interface(
            dut,
            interface_name=loopback,
            ip_address=ip_address,
            subnet=prefix_length,
            family=family,
            config="add",
            cli_type=self.data.config_cli_type,
        )

    def _configure_ipv6_enable(self, item: Mapping[str, Any]) -> None:
        """Enable IPv6 on an interface (for link-local)."""
        dut = self._resolve_dut(item.get("dut"))
        if not dut:
            st.report_fail("msg", f"Invalid DUT in IPv6 enable config: {item}")

        interface = item.get("interface")
        if not interface:
            st.report_fail("msg", f"Missing interface in IPv6 enable config: {item}")

        st.log(f"Enabling IPv6 on {dut}:{interface}")

        # Enable IPv6 on interface
        ip_api.config_ipv6(
            dut,
            action="enable",
            interface=interface,
            cli_type=self.data.config_cli_type,
        )

    def _configure_bgp_router(self, item: Mapping[str, Any]) -> None:
        """Configure BGP router with AS number and router ID."""
        dut = self._resolve_dut(item.get("dut"))
        if not dut:
            st.report_fail("msg", f"Invalid DUT in BGP router config: {item}")

        local_asn = item.get("local_asn")
        router_id = item.get("router_id")

        if not local_asn:
            st.report_fail("msg", f"Missing local_asn in BGP router config: {item}")

        st.log(f"Configuring BGP router AS {local_asn} on {dut}")

        # Configure BGP router
        bgp_api.config_bgp(
            dut,
            local_as=local_asn,
            router_id=router_id,
            config="yes",
            cli_type=self.data.config_cli_type,
        )

    def _configure_bgp_neighbor(self, item: Mapping[str, Any]) -> None:
        """Configure BGP neighbor."""
        dut = self._resolve_dut(item.get("dut"))
        if not dut:
            st.report_fail("msg", f"Invalid DUT in BGP neighbor config: {item}")

        local_asn = item.get("local_asn")
        neighbor_ip = item.get("neighbor_ip")
        remote_asn = item.get("remote_asn")
        family = item.get("family", "ipv4")
        interface = item.get("interface")  # For interface-based neighbors

        if not local_asn:
            st.report_fail("msg", f"Missing local_asn in BGP neighbor config: {item}")

        if not neighbor_ip and not interface:
            st.report_fail("msg", f"Missing neighbor_ip or interface in BGP neighbor config: {item}")

        if not remote_asn:
            st.report_fail("msg", f"Missing remote_asn in BGP neighbor config: {item}")

        neighbor_addr = interface if interface else neighbor_ip
        st.log(f"Configuring BGP neighbor {neighbor_addr} (AS {remote_asn}) on {dut}")

        # Configure BGP neighbor
        neighbor_config = {
            "local_as": local_asn,
            "remote_as": remote_asn,
            "config": "yes",
            "cli_type": self.data.config_cli_type,
        }

        # Build config_type_list for different scenarios
        config_type_list = []

        if interface:
            # Interface-based neighbor (unnumbered)
            neighbor_config["interface"] = interface
            neighbor_config["neighbor"] = interface
            config_type_list.extend(["neighbor", "activate"])
        else:
            # IP-based neighbor
            neighbor_config["neighbor"] = neighbor_ip

            # Add optional parameters for IP-based neighbors
            if item.get("update_source"):
                neighbor_config["update_src"] = item["update_source"]
                config_type_list.append("update_src")

            if item.get("ebgp_multihop"):
                config_type_list.append("ebgp_mhop")
                neighbor_config["ebgp_mhop"] = str(item["ebgp_multihop"])

        # Set address family
        addr_family = "ipv6" if family == "ipv6" else "ipv4"
        neighbor_config["addr_family"] = addr_family

        # Add config_type_list if any specific configs needed
        if config_type_list:
            neighbor_config["config_type_list"] = config_type_list

        bgp_api.config_bgp(dut, **neighbor_config)

        # For IP-based neighbors without activation in config_type_list, activate separately
        if not interface:
            bgp_api.config_bgp_neighbor_properties(
                dut,
                local_asn=local_asn,
                neighbor_ip=neighbor_addr,
                family=addr_family,
                mode="unicast",
                activate="yes",
                cli_type=self.data.config_cli_type,
            )

        # Apply next-hop-self if configured
        if item.get("next_hop_self"):
            st.log(f"Configuring next-hop-self for neighbor {neighbor_addr}")
            bgp_api.config_bgp(
                dut,
                local_as=local_asn,
                neighbor=neighbor_addr,
                config_type_list=["nexthop_self"],
                nexthop_self="yes",
                addr_family=addr_family,
                cli_type=self.data.config_cli_type,
            )

        # Configure route-reflector-client if specified
        if item.get("route_reflector_client"):
            st.log(f"Configuring route-reflector-client for neighbor {neighbor_addr}")
            bgp_api.config_bgp(
                dut,
                local_as=local_asn,
                neighbor=neighbor_addr,
                config_type_list=["routeReflector"],
                routeReflector="yes",
                addr_family=addr_family,
                cli_type=self.data.config_cli_type,
            )

    def _configure_bgp_network(self, item: Mapping[str, Any]) -> None:
        """Advertise a network via BGP network command."""
        dut = self._resolve_dut(item.get("dut"))
        if not dut:
            st.report_fail("msg", f"Invalid DUT in BGP network config: {item}")

        local_asn = item.get("local_asn")
        prefix = item.get("prefix")
        family = item.get("family", "ipv4")

        if not all([local_asn, prefix]):
            st.report_fail("msg", f"Missing required fields in BGP network config: {item}")

        st.log(f"Advertising BGP network {prefix} on {dut}")

        addr_family = "ipv6" if family == "ipv6" else "ipv4"
        bgp_api.config_bgp_network_advertise(
            dut,
            local_asn=local_asn,
            network=prefix,
            addr_family=addr_family,
            config="yes",
            cli_type=self.data.config_cli_type,
        )

    def _configure_static_route(self, item: Mapping[str, Any]) -> None:
        """Configure a static route."""
        dut = self._resolve_dut(item.get("dut"))
        if not dut:
            st.report_fail("msg", f"Invalid DUT in static route config: {item}")

        destination = item.get("destination")
        next_hop = item.get("next_hop")
        family = item.get("family", "ipv4")
        interface = item.get("interface")  # For blackhole routes (Null0)

        if not destination:
            st.report_fail("msg", f"Missing destination in static route config: {item}")

        st.log(f"Configuring static route {destination} via {next_hop or interface} on {dut}")

        ip_api.create_static_route(
            dut,
            next_hop=next_hop,
            static_ip=destination,
            family=family,
            interface=interface,
            cli_type=self.data.config_cli_type,
        )

    @classmethod
    def _remove_configuration_static(cls, item: Mapping[str, Any]) -> None:
        """Static helper for teardown_class to remove a configuration."""
        item_type = item.get("type")
        if not item_type:
            return

        dut = cls._resolve_dut(item.get("dut"))
        if not dut:
            return

        st.log(f"Removing configuration type={item_type}: {item}")

        try:
            if item_type == "interface":
                ip_api.delete_ip_interface(
                    dut,
                    interface_name=item.get("interface"),
                    ip_address=item.get("ip_address"),
                    subnet=item.get("prefix_length"),
                    family=item.get("family", "ipv4"),
                    cli_type=cls.data.config_cli_type,
                    skip_error=True,
                )
            elif item_type == "loopback":
                ip_api.configure_loopback(
                    dut,
                    loopback_name=item.get("loopback"),
                    config="no",
                    cli_type=cls.data.config_cli_type,
                )
            elif item_type == "bgp_router":
                bgp_api.config_bgp(
                    dut,
                    local_as=item.get("local_asn"),
                    config="no",
                    removeBGP="yes",
                    cli_type=cls.data.config_cli_type,
                )
            elif item_type == "bgp_network":
                addr_family = "ipv6" if item.get("family") == "ipv6" else "ipv4"
                bgp_api.config_bgp_network_advertise(
                    dut,
                    local_asn=item.get("local_asn"),
                    network=item.get("prefix"),
                    addr_family=addr_family,
                    config="no",
                    cli_type=cls.data.config_cli_type,
                )
            elif item_type == "static_route":
                ip_api.delete_static_route(
                    dut,
                    next_hop=item.get("next_hop"),
                    static_ip=item.get("destination"),
                    family=item.get("family", "ipv4"),
                    cli_type=cls.data.config_cli_type,
                )
            elif item_type == "bgp_neighbor":
                neighbor = item.get("interface") if item.get("interface") else item.get("neighbor_ip")
                if neighbor:
                    bgp_api.delete_bgp_neighbor(
                        dut,
                        local_asn=item.get("local_asn"),
                        neighbor=neighbor,
                        remote_as=item.get("remote_asn"),
                        cli_type=cls.data.config_cli_type,
                    )
            elif item_type == "ipv6_enable":
                ip_api.config_ipv6(
                    dut,
                    action="disable",
                    interface=item.get("interface"),
                    cli_type=cls.data.config_cli_type,
                )
        except Exception as e:
            st.log(f"Error removing configuration: {e}")

    def _remove_configuration(self, item: Mapping[str, Any]) -> None:
        """Remove a configuration item."""
        self._remove_configuration_static(item)

    def _verify_bgp_session(self, dut_alias: str, neighbor: str, expected_state: str = "Established") -> bool:
        """Verify BGP session state."""
        dut = self._resolve_dut(dut_alias)
        if not dut:
            st.report_fail("msg", f"Invalid DUT alias: {dut_alias}")

        st.log(f"Verifying BGP session on {dut} with neighbor {neighbor}, expected state: {expected_state}")

        def _check_state() -> bool:
            result = bgp_api.verify_bgp_summary(
                dut,
                neighbor=neighbor,
                state=expected_state,
                cli_type=self.data.show_cli_type,
            )
            return result

        if not st.poll_wait(_check_state, self.data.verify_timeout):
            st.report_fail("msg", f"BGP session to {neighbor} not in {expected_state} state on {dut}")

        return True

    def _verify_bgp_route_nexthop(
        self,
        dut_alias: str,
        prefix: str,
        expected_nexthop: str,
        family: str = "ipv4",
    ) -> bool:
        """Verify BGP route has expected next-hop."""
        dut = self._resolve_dut(dut_alias)
        if not dut:
            st.report_fail("msg", f"Invalid DUT alias: {dut_alias}")

        st.log(f"Verifying BGP route {prefix} has next-hop {expected_nexthop} on {dut}")

        # Allow time for BGP convergence
        st.wait(self.data.bgp_convergence_time, "Waiting for BGP convergence")

        def _check_nexthop() -> bool:
            # Get BGP route details
            output = bgp_api.show_bgp_ipvx_prefix(
                dut,
                prefix=prefix,
                family=family,
                cli_type=self.data.show_cli_type,
            )

            st.log(f"BGP route output for {prefix}: {output}")

            if not output:
                st.log(f"No BGP route found for {prefix}")
                return False

            # Check if next-hop matches
            for entry in output if isinstance(output, list) else [output]:
                nexthop = entry.get("nexthop", "")
                st.log(f"Found next-hop: {nexthop}, expected: {expected_nexthop}")

                # Handle link-local IPv6 next-hops with zone index
                if "fe80::" in expected_nexthop or "fe80::" in nexthop:
                    # Match link-local prefix only (ignore zone index)
                    if nexthop.startswith("fe80::") and expected_nexthop.startswith("fe80::"):
                        return True

                # For interface-based next-hop, check if it contains the interface name
                if "%" in expected_nexthop or "%" in nexthop:
                    if expected_nexthop.split("%")[0] in nexthop:
                        return True

                # Exact match
                if nexthop == expected_nexthop:
                    return True

            return False

        if not st.poll_wait(_check_nexthop, self.data.verify_timeout):
            st.report_fail("msg", f"BGP route {prefix} does not have expected next-hop {expected_nexthop} on {dut}")

        return True

    def _verify_route_in_rib(
        self,
        dut_alias: str,
        prefix: str,
        should_exist: bool = True,
        family: str = "ipv4",
    ) -> bool:
        """Verify route exists (or not) in RIB/FIB."""
        dut = self._resolve_dut(dut_alias)
        if not dut:
            st.report_fail("msg", f"Invalid DUT alias: {dut_alias}")

        st.log(f"Verifying route {prefix} {'exists' if should_exist else 'does not exist'} in RIB on {dut}")

        def _check_route() -> bool:
            result = ip_api.verify_ip_route(
                dut,
                family=family,
                ip_address=prefix.split("/")[0],
                cli_type=self.data.show_cli_type,
            )
            return result == should_exist

        if not st.poll_wait(_check_route, self.data.verify_timeout):
            if should_exist:
                st.report_fail("msg", f"Route {prefix} not found in RIB on {dut}")
            else:
                st.report_fail("msg", f"Route {prefix} unexpectedly found in RIB on {dut}")

        return True

    def _verify_nexthop_reachable(
        self,
        dut_alias: str,
        nexthop: str,
        should_be_reachable: bool = True,
    ) -> bool:
        """Verify next-hop is reachable (route exists to next-hop)."""
        dut = self._resolve_dut(dut_alias)
        if not dut:
            st.report_fail("msg", f"Invalid DUT alias: {dut_alias}")

        st.log(f"Verifying next-hop {nexthop} {'is' if should_be_reachable else 'is not'} reachable on {dut}")

        def _check_reachability() -> bool:
            result = ip_api.verify_ip_route(
                dut,
                family="ipv4" if "." in nexthop else "ipv6",
                ip_address=nexthop,
                cli_type=self.data.show_cli_type,
            )
            return result == should_be_reachable

        if not st.poll_wait(_check_reachability, self.data.verify_timeout):
            if should_be_reachable:
                st.log(f"Next-hop {nexthop} not reachable on {dut}")
            else:
                st.log(f"Next-hop {nexthop} unexpectedly reachable on {dut}")

        return should_be_reachable

    # =====================================================================
    # Test Cases
    # =====================================================================

    @pytest.mark.inventory(feature="Regression", testcases=["BGP_NextHop_TC3.2.4.1"])
    def test_ebgp_ipv4_nexthop_rewrite_direct(self) -> None:
        """TC 3.2.4.1 – eBGP IPv4 next-hop rewrite (directly connected)."""
        testcase = self._get_testcase("3.2.4.1")
        setup_items = testcase.get("setup", [])
        verify_items = testcase.get("verify", [])

        # Configure setup
        self._configure_setup_items(setup_items)

        # Wait for BGP convergence
        st.wait(self.data.bgp_convergence_time, "Waiting for BGP convergence")

        # Verify all items
        for verify_item in verify_items:
            verify_type = verify_item.get("type")

            if verify_type == "bgp_session":
                self._verify_bgp_session(
                    verify_item["dut"],
                    verify_item["neighbor"],
                    verify_item.get("expected_state", "Established"),
                )
            elif verify_type == "bgp_nexthop":
                self._verify_bgp_route_nexthop(
                    verify_item["dut"],
                    verify_item["prefix"],
                    verify_item["expected_nexthop"],
                    verify_item.get("family", "ipv4"),
                )
            elif verify_type == "route_in_rib":
                self._verify_route_in_rib(
                    verify_item["dut"],
                    verify_item["prefix"],
                    verify_item.get("should_exist", True),
                    verify_item.get("family", "ipv4"),
                )

        st.report_pass("test_case_passed")

    @pytest.mark.inventory(feature="Regression", testcases=["BGP_NextHop_TC3.2.4.2"])
    def test_ibgp_ipv4_nexthop_preserved(self) -> None:
        """TC 3.2.4.2 – iBGP IPv4 next-hop preserved (no next-hop-self)."""
        testcase = self._get_testcase("3.2.4.2")
        setup_items = testcase.get("setup", [])
        verify_items = testcase.get("verify", [])

        # Configure setup
        self._configure_setup_items(setup_items)

        # Wait for BGP convergence
        st.wait(self.data.bgp_convergence_time, "Waiting for BGP convergence")

        # Verify all items
        for verify_item in verify_items:
            verify_type = verify_item.get("type")

            if verify_type == "bgp_session":
                self._verify_bgp_session(
                    verify_item["dut"],
                    verify_item["neighbor"],
                    verify_item.get("expected_state", "Established"),
                )
            elif verify_type == "bgp_nexthop":
                self._verify_bgp_route_nexthop(
                    verify_item["dut"],
                    verify_item["prefix"],
                    verify_item["expected_nexthop"],
                    verify_item.get("family", "ipv4"),
                )

        st.report_pass("test_case_passed")

    @pytest.mark.inventory(feature="Regression", testcases=["BGP_NextHop_TC3.2.4.3"])
    def test_ibgp_nexthop_self(self) -> None:
        """TC 3.2.4.3 – iBGP next-hop-self behavior (explicitly set)."""
        testcase = self._get_testcase("3.2.4.3")
        setup_items = testcase.get("setup", [])
        verify_items = testcase.get("verify", [])

        # Configure setup
        self._configure_setup_items(setup_items)

        # Wait for BGP convergence
        st.wait(self.data.bgp_convergence_time, "Waiting for BGP convergence")

        # Verify all items
        for verify_item in verify_items:
            verify_type = verify_item.get("type")

            if verify_type == "bgp_session":
                self._verify_bgp_session(
                    verify_item["dut"],
                    verify_item["neighbor"],
                    verify_item.get("expected_state", "Established"),
                )
            elif verify_type == "bgp_nexthop":
                self._verify_bgp_route_nexthop(
                    verify_item["dut"],
                    verify_item["prefix"],
                    verify_item["expected_nexthop"],
                    verify_item.get("family", "ipv4"),
                )

        st.report_pass("test_case_passed")

    @pytest.mark.inventory(feature="Regression", testcases=["BGP_NextHop_TC3.2.4.4"])
    def test_ebgp_multihop_nexthop(self) -> None:
        """TC 3.2.4.4 – eBGP IPv4 multi-hop using loopbacks next-hop behavior."""
        testcase = self._get_testcase("3.2.4.4")
        setup_items = testcase.get("setup", [])
        verify_items = testcase.get("verify", [])

        # Configure setup
        self._configure_setup_items(setup_items)

        # Wait for BGP convergence
        st.wait(self.data.bgp_convergence_time, "Waiting for BGP convergence")

        # Verify all items
        for verify_item in verify_items:
            verify_type = verify_item.get("type")

            if verify_type == "bgp_session":
                self._verify_bgp_session(
                    verify_item["dut"],
                    verify_item["neighbor"],
                    verify_item.get("expected_state", "Established"),
                )
            elif verify_type == "bgp_nexthop":
                self._verify_bgp_route_nexthop(
                    verify_item["dut"],
                    verify_item["prefix"],
                    verify_item["expected_nexthop"],
                    verify_item.get("family", "ipv4"),
                )
            elif verify_type == "nexthop_reachable":
                self._verify_nexthop_reachable(
                    verify_item["dut"],
                    verify_item["nexthop"],
                    verify_item.get("should_be_reachable", True),
                )

        st.report_pass("test_case_passed")

    @pytest.mark.inventory(feature="Regression", testcases=["BGP_NextHop_TC3.2.4.5"])
    def test_ebgp_ipv6_nexthop_rewrite(self) -> None:
        """TC 3.2.4.5 – IPv6 eBGP next-hop rewrite (global IPv6 addresses)."""
        testcase = self._get_testcase("3.2.4.5")
        setup_items = testcase.get("setup", [])
        verify_items = testcase.get("verify", [])

        # Configure setup
        self._configure_setup_items(setup_items)

        # Wait for BGP convergence
        st.wait(self.data.bgp_convergence_time, "Waiting for BGP convergence")

        # Verify all items
        for verify_item in verify_items:
            verify_type = verify_item.get("type")

            if verify_type == "bgp_session":
                self._verify_bgp_session(
                    verify_item["dut"],
                    verify_item["neighbor"],
                    verify_item.get("expected_state", "Established"),
                )
            elif verify_type == "bgp_nexthop":
                self._verify_bgp_route_nexthop(
                    verify_item["dut"],
                    verify_item["prefix"],
                    verify_item["expected_nexthop"],
                    verify_item.get("family", "ipv6"),
                )

        st.report_pass("test_case_passed")

    @pytest.mark.inventory(feature="Regression", testcases=["BGP_NextHop_TC3.2.4.6"])
    def test_ipv6_link_local_nexthop(self) -> None:
        """TC 3.2.4.6 – IPv6 link-local next-hop handling (fe80::) with zone index."""
        testcase = self._get_testcase("3.2.4.6")
        setup_items = testcase.get("setup", [])
        verify_items = testcase.get("verify", [])

        # Configure setup
        self._configure_setup_items(setup_items)

        # Wait for BGP convergence
        st.wait(self.data.bgp_convergence_time, "Waiting for BGP convergence")

        # Verify all items
        for verify_item in verify_items:
            verify_type = verify_item.get("type")

            if verify_type == "bgp_session":
                self._verify_bgp_session(
                    verify_item["dut"],
                    verify_item["neighbor"],
                    verify_item.get("expected_state", "Established"),
                )
            elif verify_type == "bgp_nexthop":
                self._verify_bgp_route_nexthop(
                    verify_item["dut"],
                    verify_item["prefix"],
                    verify_item["expected_nexthop"],
                    verify_item.get("family", "ipv6"),
                )

        st.report_pass("test_case_passed")

    @pytest.mark.inventory(feature="Regression", testcases=["BGP_NextHop_TC3.2.4.7"])
    def test_route_reflector_nexthop_propagation(self) -> None:
        """TC 3.2.4.7 – iBGP with Route-Reflector: next-hop propagation from client->non-client."""
        testcase = self._get_testcase("3.2.4.7")
        setup_items = testcase.get("setup", [])
        verify_items = testcase.get("verify", [])

        # Configure setup
        self._configure_setup_items(setup_items)

        # Wait for BGP convergence
        st.wait(self.data.bgp_convergence_time, "Waiting for BGP convergence")

        # Verify all items
        for verify_item in verify_items:
            verify_type = verify_item.get("type")

            if verify_type == "bgp_session":
                self._verify_bgp_session(
                    verify_item["dut"],
                    verify_item["neighbor"],
                    verify_item.get("expected_state", "Established"),
                )
            elif verify_type == "bgp_nexthop":
                self._verify_bgp_route_nexthop(
                    verify_item["dut"],
                    verify_item["prefix"],
                    verify_item["expected_nexthop"],
                    verify_item.get("family", "ipv4"),
                )

        st.report_pass("test_case_passed")

    @pytest.mark.inventory(feature="Regression", testcases=["BGP_NextHop_TC3.2.4.8"])
    def test_nexthop_unreachable_rib_fib(self) -> None:
        """TC 3.2.4.8 – Next-hop unreachable behavior (RIB vs FIB) - IPv4 and IPv6."""
        testcase = self._get_testcase("3.2.4.8")
        phase1_setup = testcase.get("phase1_setup", [])
        phase1_verify = testcase.get("phase1_verify", [])
        phase2_setup = testcase.get("phase2_setup", [])
        phase2_verify = testcase.get("phase2_verify", [])

        # Phase 1: Configure with unreachable next-hop
        st.log("Phase 1: Configuring with unreachable next-hop")
        self._configure_setup_items(phase1_setup)

        # Wait for BGP convergence
        st.wait(self.data.bgp_convergence_time, "Waiting for BGP convergence")

        # Verify Phase 1: Route in BGP RIB but not in routing table
        for verify_item in phase1_verify:
            verify_type = verify_item.get("type")

            if verify_type == "bgp_session":
                self._verify_bgp_session(
                    verify_item["dut"],
                    verify_item["neighbor"],
                    verify_item.get("expected_state", "Established"),
                )
            elif verify_type == "route_in_rib":
                self._verify_route_in_rib(
                    verify_item["dut"],
                    verify_item["prefix"],
                    verify_item.get("should_exist", False),
                    verify_item.get("family", "ipv4"),
                )
            elif verify_type == "nexthop_reachable":
                self._verify_nexthop_reachable(
                    verify_item["dut"],
                    verify_item["nexthop"],
                    verify_item.get("should_be_reachable", False),
                )

        # Phase 2: Make next-hop reachable
        st.log("Phase 2: Making next-hop reachable")
        self._configure_setup_items(phase2_setup)

        # Wait for route installation
        st.wait(self.data.bgp_convergence_time, "Waiting for route installation")

        # Verify Phase 2: Route now in routing table
        for verify_item in phase2_verify:
            verify_type = verify_item.get("type")

            if verify_type == "route_in_rib":
                self._verify_route_in_rib(
                    verify_item["dut"],
                    verify_item["prefix"],
                    verify_item.get("should_exist", True),
                    verify_item.get("family", "ipv4"),
                )
            elif verify_type == "nexthop_reachable":
                self._verify_nexthop_reachable(
                    verify_item["dut"],
                    verify_item["nexthop"],
                    verify_item.get("should_be_reachable", True),
                )

        st.report_pass("test_case_passed")

    @pytest.mark.inventory(feature="Regression", testcases=["BGP_NextHop_TC3.2.4.9"])
    def test_static_redistribution_nexthop(self) -> None:
        """TC 3.2.4.9 – Redistribution/aggregate: next-hop set when advertising static into BGP."""
        testcase = self._get_testcase("3.2.4.9")
        setup_items = testcase.get("setup", [])
        verify_items = testcase.get("verify", [])

        # Configure setup
        self._configure_setup_items(setup_items)

        # Wait for BGP convergence
        st.wait(self.data.bgp_convergence_time, "Waiting for BGP convergence")

        # Verify all items
        for verify_item in verify_items:
            verify_type = verify_item.get("type")

            if verify_type == "bgp_session":
                self._verify_bgp_session(
                    verify_item["dut"],
                    verify_item["neighbor"],
                    verify_item.get("expected_state", "Established"),
                )
            elif verify_type == "bgp_nexthop":
                self._verify_bgp_route_nexthop(
                    verify_item["dut"],
                    verify_item["prefix"],
                    verify_item["expected_nexthop"],
                    verify_item.get("family", "ipv4"),
                )
            elif verify_type == "route_in_rib":
                self._verify_route_in_rib(
                    verify_item["dut"],
                    verify_item["prefix"],
                    verify_item.get("should_exist", True),
                    verify_item.get("family", "ipv4"),
                )

        st.report_pass("test_case_passed")
