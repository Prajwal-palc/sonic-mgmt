"""
BGP IPv6 Unicast Route Advertisement Test
Author: Claude Code
2025

How to run:
  ./bin/spytest --tryssh 1 \\
  --testbed ./testbeds/testbed_vs_2node.yaml \\
  tests/routing/BGP/test_bgp_ipv6_route_advertisement.py \\
  --logs-path ./logs/test_bgp_ipv6_route_advertisement_$(date +%F_%H%M%S) \\
  --log-level debug --skip-init-config --ifname-type native

Description:
  Comprehensive validation of IPv6 unicast route advertisement via BGP (Test ID 3.2.2).
  This test suite validates IPv6 network advertisements in various BGP scenarios including
  eBGP and iBGP peering, single and multiple prefix advertisements, next-hop-self
  configuration, loopback-based peering, prefix-list filtering, and bidirectional route
  exchange. Each test case performs end-to-end configuration, verification, and cleanup
  using SPyTest APIs to ensure reproducibility across hardware and virtual environments.

Pre-requisites:
  - Topology: 2-node | Supported: HW and Virtual
  - Topology Diagram:
        # Topology - 2 nodes
        # +--------------------+                       +--------------------+
        # |        D1          |                       |        D2          |
        # | Eth4 2001:db8:24::1|=======================| Eth4 2001:db8:24::2|
        # |      /64           |                       |      /64           |
        # +--------------------+                       +--------------------+

  - Feature flags / min SONiC version (if any): BGP IPv6 support
  - Required test variables (YAML): defaults.cli_type (klish required),
    defaults.verify_timeout, defaults.cleanup, defaults.min_topology,
    testcases.* definitions for all 8 sub-testcases (3.2.2.1 - 3.2.2.8)
"""

from __future__ import annotations

from collections.abc import Iterable as IterableCollection
from contextlib import contextmanager
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping

import pytest
import yaml

from spytest import SpyTestDict, st
import apis.routing.bgp as bgp_api
import apis.routing.ip as ip_api
import apis.system.interface as intf_api

VAR_FILE_ENV = "BGP_IPV6_ROUTE_ADV_VAR_FILE"
DEFAULT_VAR_FILE = (
    Path(__file__).resolve().parent / "vars_bgp_ipv6_route_advertisement.yaml"
)


def _load_yaml_data() -> Dict[str, Any]:
    """Load testcase variables from YAML with optional environment override."""
    override_path = st.getenv(VAR_FILE_ENV)
    candidate = Path(override_path) if override_path else DEFAULT_VAR_FILE

    if not candidate.is_file():
        raise FileNotFoundError(f"BGP IPv6 Route Advertisement variable file not found: {candidate}")

    with candidate.open(encoding="utf-8") as handle:
        content = yaml.safe_load(handle) or {}

    if "testcases" not in content:
        raise ValueError("BGP IPv6 Route Advertisement YAML must contain key 'testcases'")

    return content


def _iter_candidate_duts(topology: Mapping[str, Any]) -> Iterable[str]:
    """Yield DUT aliases discovered in the topology map."""
    for key, value in topology.items():
        if key.startswith("D") and value:
            yield key


@pytest.mark.topology("any")
class TestBGPIPv6RouteAdvertisement:
    """Testcases covering BGP IPv6 unicast route advertisement (Test ID 3.2.2)."""

    data = SpyTestDict()

    @classmethod
    def setup_class(cls) -> None:
        """Collect topology handles and testcase variables for the suite."""
        config = _load_yaml_data()
        defaults = config.get("defaults", {})

        min_topology = defaults.get("min_topology") or ["D1D2:1"]
        topology = st.ensure_min_topology(*min_topology)

        cls.data.config = SpyTestDict(config)
        cls.data.defaults = SpyTestDict(defaults)
        cls.data.topology = topology
        cls.data.testcases = SpyTestDict(config.get("testcases", {}))

        cls.data.cli_type = defaults.get("cli_type", "klish")
        cls.data.verify_timeout = int(defaults.get("verify_timeout", 120))
        cls.data.cleanup_enabled = bool(defaults.get("cleanup", True))
        cls.data.dut_map = SpyTestDict()

        # Map DUT aliases (D1, D2, ...) to actual device handles
        for dut_alias in _iter_candidate_duts(topology):
            cls.data.dut_map[dut_alias] = getattr(topology, dut_alias)

        cls.data.dut_names = st.get_dut_names()
        cls.data.configured_interfaces = []
        cls.data.configured_loopbacks = []
        cls.data.configured_bgp_routers = []
        cls.data.configured_bgp_neighbors = []
        cls.data.configured_bgp_networks = []
        cls.data.configured_static_routes = []
        cls.data.configured_prefix_lists = []

    @classmethod
    def teardown_class(cls) -> None:
        """Ensure all BGP and interface configurations are removed after the suite completes."""
        if not cls.data.cleanup_enabled:
            return
        cls._cleanup_all_configurations()

    def setup_method(self) -> None:
        """Reset per-test bookkeeping."""
        self._test_interfaces: List[Mapping[str, Any]] = []
        self._test_loopbacks: List[Mapping[str, Any]] = []
        self._test_bgp_routers: List[Mapping[str, Any]] = []
        self._test_bgp_neighbors: List[Mapping[str, Any]] = []
        self._test_bgp_networks: List[Mapping[str, Any]] = []
        self._test_static_routes: List[Mapping[str, Any]] = []
        self._test_prefix_lists: List[Mapping[str, Any]] = []

    def teardown_method(self) -> None:
        """Remove any configurations that the testcase created."""
        if not self.data.cleanup_enabled:
            self._test_interfaces = []
            self._test_loopbacks = []
            self._test_bgp_routers = []
            self._test_bgp_neighbors = []
            self._test_bgp_networks = []
            self._test_static_routes = []
            self._test_prefix_lists = []
            return

        # Cleanup in reverse order of configuration
        self._cleanup_prefix_lists(self._test_prefix_lists)
        self._cleanup_bgp_networks(self._test_bgp_networks)
        self._cleanup_bgp_neighbors(self._test_bgp_neighbors)
        self._cleanup_bgp_routers(self._test_bgp_routers)
        self._cleanup_static_routes(self._test_static_routes)
        self._cleanup_loopbacks(self._test_loopbacks)
        self._cleanup_interfaces(self._test_interfaces)

    @classmethod
    def _cleanup_all_configurations(cls) -> None:
        """Remove all configurations tracked across the suite."""
        cls._cleanup_prefix_lists(cls.data.configured_prefix_lists)
        cls._cleanup_bgp_networks(cls.data.configured_bgp_networks)
        cls._cleanup_bgp_neighbors(cls.data.configured_bgp_neighbors)
        cls._cleanup_bgp_routers(cls.data.configured_bgp_routers)
        cls._cleanup_static_routes(cls.data.configured_static_routes)
        cls._cleanup_loopbacks(cls.data.configured_loopbacks)
        cls._cleanup_interfaces(cls.data.configured_interfaces)

    @classmethod
    def _cleanup_interfaces(cls, interface_list: List[Mapping[str, Any]]) -> None:
        """Remove IPv6 addresses from interfaces."""
        while interface_list:
            interface = interface_list.pop()
            dut = cls._resolve_dut(interface.get("dut"))
            if not dut:
                continue
            try:
                ip_api.delete_ip_interface(
                    dut,
                    interface_name=interface.get("interface"),
                    ip_address=interface.get("ip_address"),
                    subnet=str(interface.get("prefix_length", 64)),
                    family="ipv6",
                    skip_error=True,
                    cli_type=cls.data.cli_type
                )
            except Exception as e:
                st.log(f"Error cleaning up interface {interface.get('interface')} on {interface.get('dut')}: {e}")

    @classmethod
    def _cleanup_loopbacks(cls, loopback_list: List[Mapping[str, Any]]) -> None:
        """Remove loopback interfaces."""
        while loopback_list:
            loopback = loopback_list.pop()
            dut = cls._resolve_dut(loopback.get("dut"))
            if not dut:
                continue
            try:
                # First remove IP address
                ip_api.delete_ip_interface(
                    dut,
                    interface_name=loopback.get("loopback"),
                    ip_address=loopback.get("ip_address"),
                    subnet=str(loopback.get("prefix_length", 128)),
                    family="ipv6",
                    skip_error=True,
                    cli_type=cls.data.cli_type
                )
                # Then remove loopback interface
                command = f"no interface {loopback.get('loopback')}"
                st.config(dut, command, type=cls.data.cli_type, skip_error_check=True)
            except Exception as e:
                st.log(f"Error cleaning up loopback {loopback.get('loopback')} on {loopback.get('dut')}: {e}")

    @classmethod
    def _cleanup_static_routes(cls, route_list: List[Mapping[str, Any]]) -> None:
        """Remove static routes."""
        while route_list:
            route = route_list.pop()
            dut = cls._resolve_dut(route.get("dut"))
            if not dut:
                continue
            try:
                ip_api.delete_static_route(
                    dut,
                    next_hop=route.get("next_hop"),
                    static_ip=route.get("destination"),
                    family="ipv6",
                    cli_type=cls.data.cli_type
                )
            except Exception as e:
                st.log(f"Error cleaning up static route on {route.get('dut')}: {e}")

    @classmethod
    def _cleanup_bgp_networks(cls, network_list: List[Mapping[str, Any]]) -> None:
        """Remove BGP network advertisements using klish CLI."""
        while network_list:
            network = network_list.pop()
            dut = cls._resolve_dut(network.get("dut"))
            if not dut:
                continue
            try:
                prefix = f"{network.get('network')}/{network.get('prefix_length')}"
                local_asn = network.get("local_asn")
                vrf = network.get("vrf", "default")
                addr_family = network.get("address_family", "ipv6")

                commands = []
                if vrf and vrf != "default":
                    commands.append(f"router bgp {local_asn} vrf {vrf}")
                else:
                    commands.append(f"router bgp {local_asn}")

                commands.append(f" address-family {addr_family} unicast")
                commands.append(f"  no network {prefix}")
                commands.append("  exit")
                commands.append(" exit")

                command_string = "\n".join(commands)
                st.config(dut, command_string, type="klish", skip_error_check=True)
            except Exception as e:
                st.log(f"Error cleaning up BGP network advertisement on {network.get('dut')}: {e}")

    @classmethod
    def _cleanup_bgp_neighbors(cls, neighbor_list: List[Mapping[str, Any]]) -> None:
        """Remove BGP neighbors using klish CLI."""
        while neighbor_list:
            neighbor = neighbor_list.pop()
            dut = cls._resolve_dut(neighbor.get("dut"))
            if not dut:
                continue
            try:
                local_asn = neighbor.get("local_asn")
                neighbor_ip = neighbor.get("neighbor_ip")
                vrf = neighbor.get("vrf", "default")

                commands = []
                if vrf and vrf != "default":
                    commands.append(f"router bgp {local_asn} vrf {vrf}")
                else:
                    commands.append(f"router bgp {local_asn}")

                commands.append(f" no neighbor {neighbor_ip}")
                commands.append(" exit")

                command_string = "\n".join(commands)
                st.config(dut, command_string, type="klish", skip_error_check=True)
            except Exception as e:
                st.log(f"Error cleaning up BGP neighbor on {neighbor.get('dut')}: {e}")

    @classmethod
    def _cleanup_bgp_routers(cls, router_list: List[Mapping[str, Any]]) -> None:
        """Remove BGP router instances using klish CLI."""
        while router_list:
            router = router_list.pop()
            dut = cls._resolve_dut(router.get("dut"))
            if not dut:
                continue
            try:
                local_asn = router.get("local_asn")
                vrf = router.get("vrf", "default")

                if vrf and vrf != "default":
                    command = f"no router bgp {local_asn} vrf {vrf}"
                else:
                    command = f"no router bgp {local_asn}"

                st.config(dut, command, type="klish", skip_error_check=True)
            except Exception as e:
                st.log(f"Error cleaning up BGP router on {router.get('dut')}: {e}")

    @classmethod
    def _cleanup_prefix_lists(cls, prefix_list_list: List[Mapping[str, Any]]) -> None:
        """Remove prefix lists."""
        while prefix_list_list:
            prefix_list = prefix_list_list.pop()
            dut = cls._resolve_dut(prefix_list.get("dut"))
            if not dut:
                continue
            try:
                command = f"no ipv6 prefix-list {prefix_list.get('name')}"
                st.config(dut, command, type=cls.data.cli_type, skip_error_check=True)
            except Exception as e:
                st.log(f"Error cleaning up prefix list on {prefix_list.get('dut')}: {e}")

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

    def _configure_interface(self, interface: Mapping[str, Any]) -> None:
        """Configure an IPv6 address on an interface."""
        dut = self._resolve_dut(interface.get("dut"))
        if not dut:
            st.report_fail("msg", f"Invalid DUT alias in interface definition: {interface}")

        st.log(f"Configuring IPv6 address {interface.get('ip_address')}/{interface.get('prefix_length')} "
               f"on {interface.get('interface')} on {interface.get('dut')}")

        result = ip_api.config_ip_addr_interface(
            dut,
            interface_name=interface.get("interface"),
            ip_address=interface.get("ip_address"),
            subnet=str(interface.get("prefix_length", 64)),
            family="ipv6",
            config="add",
            cli_type=self.data.cli_type
        )
        if not result:
            st.report_fail("msg", f"Failed to configure IPv6 address on {interface.get('interface')}")

        # Bring interface up
        intf_api.interface_operation(
            dut,
            interfaces=interface.get("interface"),
            operation="startup",
            cli_type=self.data.cli_type
        )

        if interface not in self._test_interfaces:
            self._test_interfaces.append(interface)
        if interface not in self.data.configured_interfaces:
            self.data.configured_interfaces.append(interface)

    def _configure_loopback(self, loopback: Mapping[str, Any]) -> None:
        """Configure a loopback interface with IPv6 address."""
        dut = self._resolve_dut(loopback.get("dut"))
        if not dut:
            st.report_fail("msg", f"Invalid DUT alias in loopback definition: {loopback}")

        st.log(f"Configuring loopback {loopback.get('loopback')} with IPv6 address "
               f"{loopback.get('ip_address')}/{loopback.get('prefix_length')} on {loopback.get('dut')}")

        # Create loopback interface
        command = f"interface {loopback.get('loopback')}"
        st.config(dut, command, type=self.data.cli_type)

        # Configure IPv6 address
        result = ip_api.config_ip_addr_interface(
            dut,
            interface_name=loopback.get("loopback"),
            ip_address=loopback.get("ip_address"),
            subnet=str(loopback.get("prefix_length", 128)),
            family="ipv6",
            config="add",
            cli_type=self.data.cli_type
        )
        if not result:
            st.report_fail("msg", f"Failed to configure IPv6 address on {loopback.get('loopback')}")

        if loopback not in self._test_loopbacks:
            self._test_loopbacks.append(loopback)
        if loopback not in self.data.configured_loopbacks:
            self.data.configured_loopbacks.append(loopback)

    def _configure_static_route(self, route: Mapping[str, Any]) -> None:
        """Configure a static IPv6 route."""
        dut = self._resolve_dut(route.get("dut"))
        if not dut:
            st.report_fail("msg", f"Invalid DUT alias in static route definition: {route}")

        st.log(f"Configuring static route {route.get('destination')} via {route.get('next_hop')} on {route.get('dut')}")

        result = ip_api.create_static_route(
            dut,
            next_hop=route.get("next_hop"),
            static_ip=route.get("destination"),
            family="ipv6",
            cli_type=self.data.cli_type
        )
        if not result:
            st.report_fail("msg", f"Failed to configure static route on {route.get('dut')}")

        if route not in self._test_static_routes:
            self._test_static_routes.append(route)
        if route not in self.data.configured_static_routes:
            self.data.configured_static_routes.append(route)

    def _configure_bgp_router(self, router: Mapping[str, Any]) -> None:
        """Configure a BGP router instance using klish CLI."""
        dut = self._resolve_dut(router.get("dut"))
        if not dut:
            st.report_fail("msg", f"Invalid DUT alias in BGP router definition: {router}")

        st.log(f"Configuring BGP router AS {router.get('local_asn')} with router-id "
               f"{router.get('router_id')} on {router.get('dut')}")

        # Build klish commands for BGP router configuration
        commands = []
        local_asn = router.get("local_asn")
        vrf = router.get("vrf", "default")

        if vrf and vrf != "default":
            commands.append(f"router bgp {local_asn} vrf {vrf}")
        else:
            commands.append(f"router bgp {local_asn}")

        if router.get("router_id"):
            commands.append(f" bgp router-id {router.get('router_id')}")

        commands.append(" exit")

        command_string = "\n".join(commands)
        st.config(dut, command_string, type="klish")

        if router not in self._test_bgp_routers:
            self._test_bgp_routers.append(router)
        if router not in self.data.configured_bgp_routers:
            self.data.configured_bgp_routers.append(router)

    def _configure_bgp_neighbor(self, neighbor: Mapping[str, Any]) -> None:
        """Configure a BGP neighbor using klish CLI."""
        dut = self._resolve_dut(neighbor.get("dut"))
        if not dut:
            st.report_fail("msg", f"Invalid DUT alias in BGP neighbor definition: {neighbor}")

        st.log(f"Configuring BGP neighbor {neighbor.get('neighbor_ip')} with remote-as "
               f"{neighbor.get('remote_asn')} on {neighbor.get('dut')}")

        # Build klish commands for BGP neighbor configuration
        commands = []
        local_asn = neighbor.get("local_asn")
        neighbor_ip = neighbor.get("neighbor_ip")
        remote_asn = neighbor.get("remote_asn")
        vrf = neighbor.get("vrf", "default")
        addr_family = neighbor.get("address_family", "ipv6")

        # Enter BGP router mode
        if vrf and vrf != "default":
            commands.append(f"router bgp {local_asn} vrf {vrf}")
        else:
            commands.append(f"router bgp {local_asn}")

        # Configure neighbor with remote-as
        commands.append(f" neighbor {neighbor_ip} remote-as {remote_asn}")

        # Configure update-source if specified
        if neighbor.get("update_source"):
            commands.append(f" neighbor {neighbor_ip} update-source {neighbor.get('update_source')}")

        # Configure ebgp-multihop if specified
        if neighbor.get("ebgp_multihop"):
            commands.append(f" neighbor {neighbor_ip} ebgp-multihop {neighbor.get('ebgp_multihop')}")

        # Enter address family mode
        commands.append(f" address-family {addr_family} unicast")

        # Activate neighbor in address family
        if neighbor.get("activate", True):
            commands.append(f"  neighbor {neighbor_ip} activate")

        # Configure next-hop-self if specified
        if neighbor.get("next_hop_self"):
            commands.append(f"  neighbor {neighbor_ip} next-hop-self")

        # Configure prefix-list filter if specified
        if neighbor.get("prefix_list_out"):
            commands.append(f"  neighbor {neighbor_ip} prefix-list {neighbor.get('prefix_list_out')} out")

        commands.append("  exit")
        commands.append(" exit")

        command_string = "\n".join(commands)
        st.config(dut, command_string, type="klish")

        if neighbor not in self._test_bgp_neighbors:
            self._test_bgp_neighbors.append(neighbor)
        if neighbor not in self.data.configured_bgp_neighbors:
            self.data.configured_bgp_neighbors.append(neighbor)

    def _configure_bgp_network(self, network: Mapping[str, Any]) -> None:
        """Configure BGP network advertisement using klish CLI."""
        dut = self._resolve_dut(network.get("dut"))
        if not dut:
            st.report_fail("msg", f"Invalid DUT alias in BGP network definition: {network}")

        prefix = f"{network.get('network')}/{network.get('prefix_length')}"
        st.log(f"Advertising BGP network {prefix} on {network.get('dut')}")

        # Build klish commands for BGP network advertisement
        commands = []
        local_asn = network.get("local_asn")
        vrf = network.get("vrf", "default")
        addr_family = network.get("address_family", "ipv6")

        # Enter BGP router mode
        if vrf and vrf != "default":
            commands.append(f"router bgp {local_asn} vrf {vrf}")
        else:
            commands.append(f"router bgp {local_asn}")

        # Enter address family mode
        commands.append(f" address-family {addr_family} unicast")

        # Advertise network
        commands.append(f"  network {prefix}")

        commands.append("  exit")
        commands.append(" exit")

        command_string = "\n".join(commands)
        st.config(dut, command_string, type="klish")

        if network not in self._test_bgp_networks:
            self._test_bgp_networks.append(network)
        if network not in self.data.configured_bgp_networks:
            self.data.configured_bgp_networks.append(network)

    def _configure_prefix_list(self, prefix_list: Mapping[str, Any]) -> None:
        """Configure IPv6 prefix list."""
        dut = self._resolve_dut(prefix_list.get("dut"))
        if not dut:
            st.report_fail("msg", f"Invalid DUT alias in prefix list definition: {prefix_list}")

        st.log(f"Configuring prefix list {prefix_list.get('name')} on {prefix_list.get('dut')}")

        command = f"ipv6 prefix-list {prefix_list.get('name')} seq {prefix_list.get('seq')} "
        command += f"{prefix_list.get('action')} {prefix_list.get('prefix')}"
        if prefix_list.get("le"):
            command += f" le {prefix_list.get('le')}"

        st.config(dut, command, type=self.data.cli_type)

        if prefix_list not in self._test_prefix_lists:
            self._test_prefix_lists.append(prefix_list)
        if prefix_list not in self.data.configured_prefix_lists:
            self.data.configured_prefix_lists.append(prefix_list)

    def _verify_bgp_session(self, verification: Mapping[str, Any]) -> None:
        """Verify BGP session establishment using click mode."""
        dut = self._resolve_dut(verification.get("dut"))
        if not dut:
            st.report_fail("msg", f"Invalid DUT alias in verification: {verification}")

        neighbor_ip = verification.get("neighbor_ip")
        st.log(f"Verifying BGP session with {neighbor_ip} on {verification.get('dut')}")

        def _check_bgp_session():
            # Use click mode for show command
            output = st.show(dut, "show bgp ipv6 summary", type="click", skip_error_check=True)
            if not output:
                st.log(f"No output from 'show bgp ipv6 summary' on {verification.get('dut')}")
                return False

            # Parse output to check if neighbor is established
            output_str = str(output)
            if neighbor_ip in output_str and ("Established" in output_str or "/Established" in output_str):
                return True

            st.log(f"BGP session with {neighbor_ip} not established yet")
            return False

        if not st.poll_wait(_check_bgp_session, self.data.verify_timeout):
            st.report_fail("msg", f"BGP session with {neighbor_ip} did not establish on {verification.get('dut')}")

    def _verify_bgp_routes(self, verification: Mapping[str, Any]) -> None:
        """Verify BGP routes are present using click mode."""
        dut = self._resolve_dut(verification.get("dut"))
        if not dut:
            st.report_fail("msg", f"Invalid DUT alias in verification: {verification}")

        expected_routes = verification.get("expected_routes", [])
        unexpected_routes = verification.get("unexpected_routes", [])

        st.log(f"Verifying BGP routes on {verification.get('dut')}")
        st.log(f"Expected routes: {expected_routes}")
        if unexpected_routes:
            st.log(f"Routes that should NOT be present: {unexpected_routes}")

        def _check_routes():
            # Use click mode for show command to check BGP routes
            output = st.show(dut, "show bgp ipv6 unicast", type="click", skip_error_check=True)
            if not output:
                st.log(f"No BGP IPv6 routes found on {verification.get('dut')}")
                # If we expect routes, this is a failure
                if expected_routes:
                    return False
                # If we only check for absence of routes, might be OK
                return not expected_routes

            output_str = str(output)

            # Check expected routes are present
            for route in expected_routes:
                # Remove /prefix_length for search if present
                route_prefix = route.split('/')[0] if '/' in route else route
                if route not in output_str and route_prefix not in output_str:
                    st.log(f"Expected route {route} not found in BGP table")
                    return False
                st.log(f"Found expected route {route}")

            # Check unexpected routes are absent
            for route in unexpected_routes:
                route_prefix = route.split('/')[0] if '/' in route else route
                if route in output_str or route_prefix in output_str:
                    st.log(f"Unexpected route {route} found in BGP table (should have been filtered)")
                    return False
                st.log(f"Confirmed route {route} is not present (as expected)")

            return True

        if not st.poll_wait(_check_routes, self.data.verify_timeout):
            # Show final state for debugging
            st.log("Final BGP table state:")
            output = st.show(dut, "show bgp ipv6 unicast", type="click", skip_error_check=True)
            st.log(str(output))
            st.report_fail("msg", f"BGP route verification failed on {verification.get('dut')}")

    def _get_testcase(self, tcid: str) -> Mapping[str, Any]:
        """Helper to fetch testcase definition from YAML."""
        testcase = self.data.testcases.get(tcid)
        if not testcase:
            st.report_fail("msg", f"Missing testcase definition for {tcid} in YAML")
        return testcase

    @pytest.mark.inventory(feature="Regression", testcases=["BGP_IPv6_TC3.2.2.1"])
    def test_bgp_ipv6_ebgp_single_prefix(self) -> None:
        """TC 3.2.2.1 - Basic IPv6 Network Advertisement via eBGP (Single Prefix)."""
        testcase = self._get_testcase("3.2.2.1")

        st.log("=" * 80)
        st.log(f"Test Case 3.2.2.1: {testcase.get('title')}")
        st.log(f"Description: {testcase.get('description')}")
        st.log("=" * 80)

        # Configure interfaces
        for interface in testcase.get("interfaces", []):
            self._configure_interface(interface)

        # Configure loopbacks
        for loopback in testcase.get("loopbacks", []):
            self._configure_loopback(loopback)

        # Configure BGP routers
        for router in testcase.get("bgp_routers", []):
            self._configure_bgp_router(router)

        # Configure BGP neighbors
        for neighbor in testcase.get("bgp_neighbors", []):
            self._configure_bgp_neighbor(neighbor)

        # Configure BGP networks
        for network in testcase.get("bgp_networks", []):
            self._configure_bgp_network(network)

        # Wait for BGP convergence
        st.wait(10, "Waiting for BGP session establishment and route advertisement")

        # Verify BGP sessions and routes
        for verification in testcase.get("verification", []):
            self._verify_bgp_routes(verification)

        st.report_pass("test_case_passed")

    @pytest.mark.inventory(feature="Regression", testcases=["BGP_IPv6_TC3.2.2.2"])
    def test_bgp_ipv6_ebgp_multiple_prefixes(self) -> None:
        """TC 3.2.2.2 - Multiple IPv6 Network Advertisements via eBGP."""
        testcase = self._get_testcase("3.2.2.2")

        st.log("=" * 80)
        st.log(f"Test Case 3.2.2.2: {testcase.get('title')}")
        st.log(f"Description: {testcase.get('description')}")
        st.log("=" * 80)

        # Configure interfaces
        for interface in testcase.get("interfaces", []):
            self._configure_interface(interface)

        # Configure loopbacks
        for loopback in testcase.get("loopbacks", []):
            self._configure_loopback(loopback)

        # Configure BGP routers
        for router in testcase.get("bgp_routers", []):
            self._configure_bgp_router(router)

        # Configure BGP neighbors
        for neighbor in testcase.get("bgp_neighbors", []):
            self._configure_bgp_neighbor(neighbor)

        # Configure BGP networks
        for network in testcase.get("bgp_networks", []):
            self._configure_bgp_network(network)

        # Wait for BGP convergence
        st.wait(10, "Waiting for BGP session establishment and route advertisement")

        # Verify BGP sessions and routes
        for verification in testcase.get("verification", []):
            self._verify_bgp_routes(verification)

        st.report_pass("test_case_passed")

    @pytest.mark.inventory(feature="Regression", testcases=["BGP_IPv6_TC3.2.2.3"])
    def test_bgp_ipv6_ibgp_single_prefix(self) -> None:
        """TC 3.2.2.3 - IPv6 Network Advertisement via iBGP (Single Prefix)."""
        testcase = self._get_testcase("3.2.2.3")

        st.log("=" * 80)
        st.log(f"Test Case 3.2.2.3: {testcase.get('title')}")
        st.log(f"Description: {testcase.get('description')}")
        st.log("=" * 80)

        # Configure interfaces
        for interface in testcase.get("interfaces", []):
            self._configure_interface(interface)

        # Configure loopbacks
        for loopback in testcase.get("loopbacks", []):
            self._configure_loopback(loopback)

        # Configure BGP routers
        for router in testcase.get("bgp_routers", []):
            self._configure_bgp_router(router)

        # Configure BGP neighbors
        for neighbor in testcase.get("bgp_neighbors", []):
            self._configure_bgp_neighbor(neighbor)

        # Configure BGP networks
        for network in testcase.get("bgp_networks", []):
            self._configure_bgp_network(network)

        # Wait for BGP convergence
        st.wait(10, "Waiting for BGP session establishment and route advertisement")

        # Verify BGP sessions and routes
        for verification in testcase.get("verification", []):
            self._verify_bgp_routes(verification)

        st.report_pass("test_case_passed")

    @pytest.mark.inventory(feature="Regression", testcases=["BGP_IPv6_TC3.2.2.4"])
    def test_bgp_ipv6_ibgp_multiple_prefixes(self) -> None:
        """TC 3.2.2.4 - IPv6 Network Advertisement via iBGP (Multiple Prefixes)."""
        testcase = self._get_testcase("3.2.2.4")

        st.log("=" * 80)
        st.log(f"Test Case 3.2.2.4: {testcase.get('title')}")
        st.log(f"Description: {testcase.get('description')}")
        st.log("=" * 80)

        # Configure interfaces
        for interface in testcase.get("interfaces", []):
            self._configure_interface(interface)

        # Configure loopbacks
        for loopback in testcase.get("loopbacks", []):
            self._configure_loopback(loopback)

        # Configure BGP routers
        for router in testcase.get("bgp_routers", []):
            self._configure_bgp_router(router)

        # Configure BGP neighbors
        for neighbor in testcase.get("bgp_neighbors", []):
            self._configure_bgp_neighbor(neighbor)

        # Configure BGP networks
        for network in testcase.get("bgp_networks", []):
            self._configure_bgp_network(network)

        # Wait for BGP convergence
        st.wait(10, "Waiting for BGP session establishment and route advertisement")

        # Verify BGP sessions and routes
        for verification in testcase.get("verification", []):
            self._verify_bgp_routes(verification)

        st.report_pass("test_case_passed")

    @pytest.mark.inventory(feature="Regression", testcases=["BGP_IPv6_TC3.2.2.5"])
    def test_bgp_ipv6_ibgp_next_hop_self(self) -> None:
        """TC 3.2.2.5 - IPv6 Network Advertisement with Next-Hop-Self (iBGP)."""
        testcase = self._get_testcase("3.2.2.5")

        st.log("=" * 80)
        st.log(f"Test Case 3.2.2.5: {testcase.get('title')}")
        st.log(f"Description: {testcase.get('description')}")
        st.log("=" * 80)

        # Configure interfaces
        for interface in testcase.get("interfaces", []):
            self._configure_interface(interface)

        # Configure loopbacks
        for loopback in testcase.get("loopbacks", []):
            self._configure_loopback(loopback)

        # Configure static routes
        for route in testcase.get("static_routes", []):
            self._configure_static_route(route)

        # Configure BGP routers
        for router in testcase.get("bgp_routers", []):
            self._configure_bgp_router(router)

        # Configure BGP neighbors
        for neighbor in testcase.get("bgp_neighbors", []):
            self._configure_bgp_neighbor(neighbor)

        # Configure BGP networks
        for network in testcase.get("bgp_networks", []):
            self._configure_bgp_network(network)

        # Wait for BGP convergence
        st.wait(15, "Waiting for BGP session establishment over loopbacks")

        # Verify BGP sessions and routes
        for verification in testcase.get("verification", []):
            self._verify_bgp_routes(verification)

        st.report_pass("test_case_passed")

    @pytest.mark.inventory(feature="Regression", testcases=["BGP_IPv6_TC3.2.2.6"])
    def test_bgp_ipv6_ebgp_loopback_based(self) -> None:
        """TC 3.2.2.6 - IPv6 Network Advertisement from Loopback Addresses."""
        testcase = self._get_testcase("3.2.2.6")

        st.log("=" * 80)
        st.log(f"Test Case 3.2.2.6: {testcase.get('title')}")
        st.log(f"Description: {testcase.get('description')}")
        st.log("=" * 80)

        # Configure interfaces
        for interface in testcase.get("interfaces", []):
            self._configure_interface(interface)

        # Configure loopbacks
        for loopback in testcase.get("loopbacks", []):
            self._configure_loopback(loopback)

        # Configure static routes
        for route in testcase.get("static_routes", []):
            self._configure_static_route(route)

        # Configure BGP routers
        for router in testcase.get("bgp_routers", []):
            self._configure_bgp_router(router)

        # Configure BGP neighbors
        for neighbor in testcase.get("bgp_neighbors", []):
            self._configure_bgp_neighbor(neighbor)

        # Configure BGP networks
        for network in testcase.get("bgp_networks", []):
            self._configure_bgp_network(network)

        # Wait for BGP convergence
        st.wait(15, "Waiting for BGP session establishment over loopbacks with multi-hop")

        # Verify BGP sessions and routes
        for verification in testcase.get("verification", []):
            self._verify_bgp_routes(verification)

        st.report_pass("test_case_passed")

    @pytest.mark.inventory(feature="Regression", testcases=["BGP_IPv6_TC3.2.2.7"])
    def test_bgp_ipv6_prefix_list_filtering(self) -> None:
        """TC 3.2.2.7 - IPv6 Network Advertisement with Prefix-List Filtering."""
        testcase = self._get_testcase("3.2.2.7")

        st.log("=" * 80)
        st.log(f"Test Case 3.2.2.7: {testcase.get('title')}")
        st.log(f"Description: {testcase.get('description')}")
        st.log("=" * 80)

        # Configure interfaces
        for interface in testcase.get("interfaces", []):
            self._configure_interface(interface)

        # Configure loopbacks
        for loopback in testcase.get("loopbacks", []):
            self._configure_loopback(loopback)

        # Configure prefix lists
        for prefix_list in testcase.get("prefix_lists", []):
            self._configure_prefix_list(prefix_list)

        # Configure BGP routers
        for router in testcase.get("bgp_routers", []):
            self._configure_bgp_router(router)

        # Configure BGP neighbors
        for neighbor in testcase.get("bgp_neighbors", []):
            self._configure_bgp_neighbor(neighbor)

        # Configure BGP networks
        for network in testcase.get("bgp_networks", []):
            self._configure_bgp_network(network)

        # Wait for BGP convergence
        st.wait(10, "Waiting for BGP session establishment and filtered route advertisement")

        # Verify BGP sessions and routes (including absent routes)
        for verification in testcase.get("verification", []):
            self._verify_bgp_routes(verification)

        st.report_pass("test_case_passed")

    @pytest.mark.inventory(feature="Regression", testcases=["BGP_IPv6_TC3.2.2.8"])
    def test_bgp_ipv6_bidirectional_exchange(self) -> None:
        """TC 3.2.2.8 - IPv6 Network Advertisement with Bidirectional Exchange."""
        testcase = self._get_testcase("3.2.2.8")

        st.log("=" * 80)
        st.log(f"Test Case 3.2.2.8: {testcase.get('title')}")
        st.log(f"Description: {testcase.get('description')}")
        st.log("=" * 80)

        # Configure interfaces
        for interface in testcase.get("interfaces", []):
            self._configure_interface(interface)

        # Configure loopbacks
        for loopback in testcase.get("loopbacks", []):
            self._configure_loopback(loopback)

        # Configure BGP routers
        for router in testcase.get("bgp_routers", []):
            self._configure_bgp_router(router)

        # Configure BGP neighbors
        for neighbor in testcase.get("bgp_neighbors", []):
            self._configure_bgp_neighbor(neighbor)

        # Configure BGP networks
        for network in testcase.get("bgp_networks", []):
            self._configure_bgp_network(network)

        # Wait for BGP convergence
        st.wait(10, "Waiting for BGP session establishment and bidirectional route exchange")

        # Verify BGP sessions and routes on both DUTs
        for verification in testcase.get("verification", []):
            self._verify_bgp_routes(verification)

        st.report_pass("test_case_passed")
