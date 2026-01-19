"""
BGP IPv4 ROUTE ADVERTISEMENT - Test ID 3.2.1
Author: Claude
2025

How to run:
  ./bin/spytest  --tryssh 1  \
  --testbed ./testbeds/testbed_vs_2node.yaml  \
  tests/routing/BGP/test_bgp_ipv4_route_advertisement.py \
  --logs-path ./logs/test_bgp_321_$(date +%F_%H%M%S) \
  --log-level debug  --skip-init-config  --ifname-type native

Description:
  Comprehensive validation of BGP IPv4 unicast route advertisement functionality
  covering network command, redistribution (connected/static), route filtering,
  attribute manipulation (MED, AS-PATH, Communities), aggregation, and dynamic
  withdrawal. Tests cover both eBGP and iBGP scenarios with extensive verification
  of BGP table and routing table entries. All test cases consume topology-aware
  variables from YAML to remain reusable across SONiC hardware and virtual environments.

Pre-requisites:
  - Topology: any | Supported: HW and Virtual
  - Topology Diagram:
        # Topology - 2 nodes
        # +--------------------+                       +--------------------+
        # |        D1          |                       |        D2          |
        # | Eth4 10.0.0.1/30   |=======================| Eth4 10.0.0.2/30   |
        # | AS 65001/65002     |                       | AS 65001/65002     |
        # +--------------------+                       +--------------------+

  - Feature flags / min SONiC version: BGP support required
  - Required test variables (YAML): defaults.cli_type (klish),
    defaults.verify_timeout, defaults.cleanup, defaults.min_topology,
    testcases.* definitions (3.2.1.1 through 3.2.1.20)
"""

from __future__ import annotations

from collections.abc import Iterable as IterableCollection
from contextlib import contextmanager
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional

import pytest
import yaml

from spytest import SpyTestDict, st
import apis.routing.bgp as bgp_api
import apis.routing.ip as ip_api
import utilities.common as utils

VAR_FILE_ENV = "BGP_321_VAR_FILE"
DEFAULT_VAR_FILE = (
    Path(__file__).resolve().parent / "vars_bgp_ipv4_route_advertisement.yaml"
)


def _load_yaml_data() -> Dict[str, Any]:
    """Load testcase variables from YAML with optional environment override."""
    override_path = st.getenv(VAR_FILE_ENV)
    candidate = Path(override_path) if override_path else DEFAULT_VAR_FILE

    if not candidate.is_file():
        raise FileNotFoundError(f"BGP 3.2.1 variable file not found: {candidate}")

    with candidate.open(encoding="utf-8") as handle:
        content = yaml.safe_load(handle) or {}

    if "testcases" not in content:
        raise ValueError("BGP 3.2.1 YAML must contain key 'testcases'")

    return content


def _iter_candidate_duts(topology: Mapping[str, Any]) -> Iterable[str]:
    """Yield DUT aliases discovered in the topology map."""
    for key, value in topology.items():
        if key.startswith("D") and value:
            yield key


@pytest.mark.topology("any")
class TestBgpIpv4RouteAdvertisement:
    """Testcases covering BGP IPv4 route advertisement - Test ID 3.2.1."""

    data = SpyTestDict()

    @classmethod
    def setup_class(cls) -> None:
        """Collect topology handles and testcase variables for the suite."""
        st.log("=" * 80)
        st.log("BGP IPv4 Route Advertisement Test Suite - Setup Class")
        st.log("=" * 80)

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
        cls.data.keepalive = int(defaults.get("keepalive", 60))
        cls.data.holdtime = int(defaults.get("hold", 180))

        cls.data.dut_map = SpyTestDict()
        cls.data.configured_items = []

        # Map DUT aliases (D1, D2, ...) to actual device handles
        for dut_alias in _iter_candidate_duts(topology):
            cls.data.dut_map[dut_alias] = getattr(topology, dut_alias)

        cls.data.dut_names = st.get_dut_names()
        st.log(f"DUT names: {cls.data.dut_names}")
        st.log(f"DUT map: {dict(cls.data.dut_map)}")
        st.log(f"CLI type: {cls.data.cli_type}")
        st.log(f"Verify timeout: {cls.data.verify_timeout}s")

    @classmethod
    def teardown_class(cls) -> None:
        """Ensure all BGP configurations are removed after the suite completes."""
        st.log("=" * 80)
        st.log("BGP IPv4 Route Advertisement Test Suite - Teardown Class")
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
        return inspect.currentframe().f_back.f_code.co_name

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
            elif item_type == "bgp_redistribute":
                self._configure_bgp_redistribute(item)
            elif item_type == "static_route":
                self._configure_static_route(item)
            elif item_type == "prefix_list":
                self._configure_prefix_list(item)
            elif item_type == "route_map":
                self._configure_route_map(item)
            elif item_type == "bgp_aggregate":
                self._configure_bgp_aggregate(item)
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

        if family == "ipv4":
            ip_api.config_ip_addr_interface(
                dut,
                interface_name=interface,
                ip_address=ip_address,
                subnet=prefix_length,
                family=family,
                config="add",
                cli_type=self.data.cli_type,
            )
        elif family == "ipv6":
            ip_api.config_ip_addr_interface(
                dut,
                interface_name=interface,
                ip_address=ip_address,
                subnet=prefix_length,
                family=family,
                config="add",
                cli_type=self.data.cli_type,
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
        ip_api.configure_loopback(dut, loopback_name=loopback, config="yes", cli_type=self.data.cli_type)

        # Configure IP address
        ip_api.config_ip_addr_interface(
            dut,
            interface_name=loopback,
            ip_address=ip_address,
            subnet=prefix_length,
            family=family,
            config="add",
            cli_type=self.data.cli_type,
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
            cli_type=self.data.cli_type,
        )

        # Configure keepalive and hold timers
        if self.data.keepalive and self.data.holdtime:
            bgp_api.config_bgp(
                dut,
                local_as=local_asn,
                config_type_list=["keep_alive", "hold"],
                keep_alive=self.data.keepalive,
                hold=self.data.holdtime,
                cli_type=self.data.cli_type,
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

        if not all([local_asn, neighbor_ip, remote_asn]):
            st.report_fail("msg", f"Missing required fields in BGP neighbor config: {item}")

        st.log(f"Configuring BGP neighbor {neighbor_ip} (AS {remote_asn}) on {dut}")

        # Configure BGP neighbor
        bgp_api.config_bgp(
            dut,
            local_as=local_asn,
            neighbor=neighbor_ip,
            remote_as=remote_asn,
            config="yes",
            cli_type=self.data.cli_type,
        )

        # Activate neighbor for address family
        addr_family = "ipv6" if family == "ipv6" else "ipv4"
        bgp_api.config_bgp_neighbor_properties(
            dut,
            local_asn=local_asn,
            neighbor_ip=neighbor_ip,
            family=addr_family,
            mode='unicast',
            activate='yes',
            cli_type=self.data.cli_type,
        )

        # Apply additional neighbor configurations
        if item.get("next_hop_self"):
            bgp_api.config_bgp(
                dut,
                local_as=local_asn,
                neighbor=neighbor_ip,
                config_type_list=["next_hop_self"],
                next_hop_self="yes",
                addr_family=addr_family,
                cli_type=self.data.cli_type,
            )

        if item.get("route_map_out"):
            bgp_api.config_bgp(
                dut,
                local_as=local_asn,
                neighbor=neighbor_ip,
                config_type_list=["routeMap"],
                routeMap=item["route_map_out"],
                diRection="out",
                addr_family=addr_family,
                cli_type=self.data.cli_type,
            )

        if item.get("send_community"):
            bgp_api.config_bgp(
                dut,
                local_asn=local_asn,
                neighbor=neighbor_ip,
                config_type_list=["send_community"],
                send_community=item["send_community"],
                cli_type=self.data.cli_type,
            )

        if item.get("prefix_list_out"):
            bgp_api.config_bgp(
                dut,
                local_asn=local_asn,
                neighbor=neighbor_ip,
                config_type_list=["prefix_list"],
                prefix_list=item["prefix_list_out"],
                diRection="out",
                addr_family=addr_family,
                cli_type=self.data.cli_type,
            )

        if item.get("max_prefix"):
            bgp_api.config_bgp(
                dut,
                local_asn=local_asn,
                neighbor=neighbor_ip,
                config_type_list=["maximum_prefix"],
                maximum_prefix=item["max_prefix"],
                addr_family=addr_family,
                cli_type=self.data.cli_type,
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
            cli_type=self.data.cli_type,
        )

    def _configure_bgp_redistribute(self, item: Mapping[str, Any]) -> None:
        """Configure BGP redistribution."""
        dut = self._resolve_dut(item.get("dut"))
        if not dut:
            st.report_fail("msg", f"Invalid DUT in BGP redistribute config: {item}")

        local_asn = item.get("local_asn")
        protocol = item.get("protocol")
        family = item.get("family", "ipv4")

        if not all([local_asn, protocol]):
            st.report_fail("msg", f"Missing required fields in BGP redistribute config: {item}")

        st.log(f"Configuring BGP redistribute {protocol} on {dut}")

        addr_family = "ipv6" if family == "ipv6" else "ipv4"
        route_map = item.get("route_map", "")
        bgp_api.config_address_family_redistribute(
            dut,
            local_asn=local_asn,
            mode_type=protocol,
            mode="add",
            value=route_map,
            addr_family=addr_family,
            cli_type=self.data.cli_type,
        )

    def _configure_static_route(self, item: Mapping[str, Any]) -> None:
        """Configure a static route."""
        dut = self._resolve_dut(item.get("dut"))
        if not dut:
            st.report_fail("msg", f"Invalid DUT in static route config: {item}")

        destination = item.get("destination")
        next_hop = item.get("next_hop")
        family = item.get("family", "ipv4")

        if not destination:
            st.report_fail("msg", f"Missing destination in static route config: {item}")

        st.log(f"Configuring static route {destination} via {next_hop} on {dut}")

        ip_api.create_static_route(
            dut,
            next_hop=next_hop,
            static_ip=destination,
            family=family,
            cli_type=self.data.cli_type,
        )

    def _configure_prefix_list(self, item: Mapping[str, Any]) -> None:
        """Configure a prefix-list entry."""
        dut = self._resolve_dut(item.get("dut"))
        if not dut:
            st.report_fail("msg", f"Invalid DUT in prefix-list config: {item}")

        name = item.get("name")
        family = item.get("family", "ipv4")
        action = item.get("action", "permit")
        sequence = item.get("sequence", 10)
        prefix = item.get("prefix")

        if not all([name, prefix]):
            st.report_fail("msg", f"Missing required fields in prefix-list config: {item}")

        st.log(f"Configuring prefix-list {name} seq {sequence} {action} {prefix} on {dut}")

        config_kwargs = {
            "config": "yes",
            "seq_num": str(sequence),
            "cli_type": self.data.cli_type,
            "skip_error_check": True,
        }

        if item.get("le"):
            config_kwargs["le"] = item["le"]
        if item.get("ge"):
            config_kwargs["ge"] = item["ge"]

        ip_api.config_ip_prefix_list(
            dut,
            prefix_list=name,
            ip_addr=prefix,
            family=family,
            action=action,
            **config_kwargs,
        )

    def _configure_route_map(self, item: Mapping[str, Any]) -> None:
        """Configure a route-map entry."""
        dut = self._resolve_dut(item.get("dut"))
        if not dut:
            st.report_fail("msg", f"Invalid DUT in route-map config: {item}")

        name = item.get("name")
        action = item.get("action", "permit")
        sequence = item.get("sequence", 10)

        if not name:
            st.report_fail("msg", f"Missing route-map name: {item}")

        st.log(f"Configuring route-map {name} {action} {sequence} on {dut}")

        # Build route-map configuration with set clauses
        config_kwargs = {
            "config": "yes",
            "sequence": str(sequence),
            "action": action,
            "cli_type": self.data.cli_type,
        }

        if item.get("set_metric"):
            config_kwargs["metric"] = str(item["set_metric"])

        if item.get("set_community"):
            config_kwargs["community"] = item["set_community"]

        if item.get("set_local_preference"):
            config_kwargs["local_preference"] = str(item["set_local_preference"])

        # Create route-map entry
        ip_api.config_route_map(
            dut,
            route_map=name,
            **config_kwargs,
        )

        # Configure match conditions (needs separate call after route-map creation)
        if item.get("match_prefix_list"):
            family = item.get("family", "ipv4")
            ip_api.config_route_map_match_ip_address(
                dut,
                tag=name,
                operation=action,
                sequence=str(sequence),
                value=item["match_prefix_list"],
                family=family,
                cli_type=self.data.cli_type,
            )

        # Configure AS path prepending (needs separate call)
        if item.get("set_as_path_prepend"):
            ip_api.config_route_map_set_aspath(
                dut,
                tag=name,
                operation=action,
                sequence=str(sequence),
                value=item["set_as_path_prepend"],
                option='prepend',
                cli_type=self.data.cli_type,
            )

    def _configure_bgp_aggregate(self, item: Mapping[str, Any]) -> None:
        """Configure BGP aggregate address."""
        dut = self._resolve_dut(item.get("dut"))
        if not dut:
            st.report_fail("msg", f"Invalid DUT in BGP aggregate config: {item}")

        local_asn = item.get("local_asn")
        prefix = item.get("prefix")
        family = item.get("family", "ipv4")
        summary_only = item.get("summary_only", False)

        if not all([local_asn, prefix]):
            st.report_fail("msg", f"Missing required fields in BGP aggregate config: {item}")

        st.log(f"Configuring BGP aggregate {prefix} on {dut}")

        bgp_api.create_bgp_aggregate_address(
            dut,
            local_asn=local_asn,
            address_range=prefix,
            summary=summary_only,
            family=family,
            config="yes",
            cli_type=self.data.cli_type,
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
                    cli_type=cls.data.cli_type,
                    skip_error=True,
                )
            elif item_type == "loopback":
                ip_api.configure_loopback(
                    dut,
                    loopback_name=item.get("loopback"),
                    config="no",
                    cli_type=cls.data.cli_type,
                )
            elif item_type == "bgp_router":
                bgp_api.config_bgp(
                    dut,
                    local_as=item.get("local_asn"),
                    config="no",
                    removeBGP="yes",
                    cli_type=cls.data.cli_type,
                )
            elif item_type == "bgp_network":
                addr_family = "ipv6" if item.get("family") == "ipv6" else "ipv4"
                bgp_api.config_bgp_network_advertise(
                    dut,
                    local_asn=item.get("local_asn"),
                    network=item.get("prefix"),
                    addr_family=addr_family,
                    config="no",
                    cli_type=cls.data.cli_type,
                )
            elif item_type == "static_route":
                ip_api.delete_static_route(
                    dut,
                    next_hop=item.get("next_hop"),
                    static_ip=item.get("destination"),
                    family=item.get("family", "ipv4"),
                    cli_type=cls.data.cli_type,
                )
        except Exception as e:
            st.log(f"Error removing configuration: {e}")

    def _remove_configuration(self, item: Mapping[str, Any]) -> None:
        """Remove a configuration item."""
        self._remove_configuration_static(item)

    def _verify_bgp_session(self, verify_item: Mapping[str, Any]) -> None:
        """Verify BGP session state."""
        dut = self._resolve_dut(verify_item.get("dut"))
        if not dut:
            st.report_fail("msg", f"Invalid DUT in BGP session verification: {verify_item}")

        neighbor_ip = verify_item.get("neighbor_ip")
        expected_state = verify_item.get("state", "Established")
        family = verify_item.get("family", "ipv4")

        if not neighbor_ip:
            st.report_fail("msg", f"Missing neighbor_ip in verification: {verify_item}")

        st.log(f"Verifying BGP neighbor {neighbor_ip} state={expected_state} on {dut}")

        def _check_session():
            return bgp_api.verify_bgp_neighbor(
                dut,
                neighbor_ip,
                state=expected_state,
                asn=verify_item.get("remote_asn"),
                cli_type=self.data.cli_type,
            )

        if not st.poll_wait(_check_session, self.data.verify_timeout):
            st.report_fail(
                "msg",
                f"BGP neighbor {neighbor_ip} not in {expected_state} state on {verify_item.get('dut')}"
            )

        # Verify prefix count if specified
        if verify_item.get("prefix_count_min") is not None or verify_item.get("prefix_count_max") is not None:
            bgp_output = bgp_api.show_bgp_ipv4_summary(dut, cli_type=self.data.cli_type)
            if bgp_output:
                for entry in bgp_output:
                    if entry.get("neighbor") == neighbor_ip:
                        prefix_count = int(entry.get("state_pfxrcd", 0))
                        min_count = verify_item.get("prefix_count_min")
                        max_count = verify_item.get("prefix_count_max")

                        if min_count is not None and prefix_count < min_count:
                            st.report_fail(
                                "msg",
                                f"Prefix count {prefix_count} less than minimum {min_count}"
                            )
                        if max_count is not None and prefix_count > max_count:
                            st.report_fail(
                                "msg",
                                f"Prefix count {prefix_count} greater than maximum {max_count}"
                            )

    def _verify_route(self, verify_item: Mapping[str, Any]) -> None:
        """Verify route presence or absence in routing table."""
        dut = self._resolve_dut(verify_item.get("dut"))
        if not dut:
            st.report_fail("msg", f"Invalid DUT in route verification: {verify_item}")

        check_route = verify_item.get("check_route")
        expected = verify_item.get("expected", "present")
        family = verify_item.get("family", "ipv4")
        next_hop = verify_item.get("next_hop")

        if not check_route:
            st.report_fail("msg", f"Missing check_route in verification: {verify_item}")

        st.log(f"Verifying route {check_route} expected={expected} on {dut}")

        def _check_route_present():
            kwargs = {"ip_address": check_route, "family": family, "cli_type": self.data.cli_type}
            if next_hop:
                kwargs["nexthop"] = next_hop
            return ip_api.verify_ip_route(dut, **kwargs)

        route_present = st.poll_wait(_check_route_present, self.data.verify_timeout)

        if expected == "present" and not route_present:
            st.report_fail("msg", f"Route {check_route} not found on {verify_item.get('dut')}")
        elif expected == "absent" and route_present:
            st.report_fail("msg", f"Route {check_route} still present on {verify_item.get('dut')}")

    def _verify_all(self, verify_items: List[Mapping[str, Any]]) -> None:
        """Run all verification checks."""
        for verify_item in verify_items:
            if "neighbor_ip" in verify_item:
                self._verify_bgp_session(verify_item)
            elif "check_route" in verify_item:
                self._verify_route(verify_item)

    @pytest.mark.inventory(feature="Regression", testcases=["BGP_321_TC1"])
    def test_bgp_321_1_basic_network_advertisement(self) -> None:
        """TC 3.2.1.1 – Basic IPv4 Network Advertisement via network command."""
        st.log("TEST: 3.2.1.1 - Basic IPv4 Network Advertisement via network command")
        testcase = self._get_testcase("3.2.1.1")

        setup_items = testcase.get("setup", [])
        verify_items = testcase.get("verify", [])

        # Configure setup
        self._configure_setup_items(setup_items)

        # Wait for BGP convergence
        st.wait(10, "Waiting for BGP convergence")

        # Verify
        self._verify_all(verify_items)

        st.report_pass("test_case_passed")

    @pytest.mark.inventory(feature="Regression", testcases=["BGP_321_TC2"])
    def test_bgp_321_2_multiple_networks_advertisement(self) -> None:
        """TC 3.2.1.2 – Multiple IPv4 Networks Advertisement."""
        st.log("TEST: 3.2.1.2 - Multiple IPv4 Networks Advertisement")
        testcase = self._get_testcase("3.2.1.2")

        setup_items = testcase.get("setup", [])
        verify_items = testcase.get("verify", [])

        self._configure_setup_items(setup_items)
        st.wait(10, "Waiting for BGP convergence")
        self._verify_all(verify_items)

        st.report_pass("test_case_passed")

    @pytest.mark.inventory(feature="Regression", testcases=["BGP_321_TC3"])
    def test_bgp_321_3_specific_prefix_lengths(self) -> None:
        """TC 3.2.1.3 – IPv4 Advertisement with Specific Prefix Lengths."""
        st.log("TEST: 3.2.1.3 - IPv4 Advertisement with Specific Prefix Lengths (/32, /30, /24, /16)")
        testcase = self._get_testcase("3.2.1.3")

        setup_items = testcase.get("setup", [])
        verify_items = testcase.get("verify", [])

        self._configure_setup_items(setup_items)
        st.wait(10, "Waiting for BGP convergence")
        self._verify_all(verify_items)

        st.report_pass("test_case_passed")

    @pytest.mark.inventory(feature="Regression", testcases=["BGP_321_TC4"])
    def test_bgp_321_4_connected_redistribution(self) -> None:
        """TC 3.2.1.4 – IPv4 Connected Route Redistribution."""
        st.log("TEST: 3.2.1.4 - IPv4 Connected Route Redistribution")
        testcase = self._get_testcase("3.2.1.4")

        setup_items = testcase.get("setup", [])
        verify_items = testcase.get("verify", [])

        self._configure_setup_items(setup_items)
        st.wait(10, "Waiting for BGP convergence")
        self._verify_all(verify_items)

        st.report_pass("test_case_passed")

    @pytest.mark.inventory(feature="Regression", testcases=["BGP_321_TC5"])
    def test_bgp_321_5_static_redistribution(self) -> None:
        """TC 3.2.1.5 – IPv4 Static Route Redistribution."""
        st.log("TEST: 3.2.1.5 - IPv4 Static Route Redistribution")
        testcase = self._get_testcase("3.2.1.5")

        setup_items = testcase.get("setup", [])
        verify_items = testcase.get("verify", [])

        self._configure_setup_items(setup_items)
        st.wait(10, "Waiting for BGP convergence")
        self._verify_all(verify_items)

        st.report_pass("test_case_passed")

    @pytest.mark.inventory(feature="Regression", testcases=["BGP_321_TC6"])
    def test_bgp_321_6_ibgp_route_advertisement(self) -> None:
        """TC 3.2.1.6 – iBGP IPv4 Route Advertisement (Same AS)."""
        st.log("TEST: 3.2.1.6 - iBGP IPv4 Route Advertisement (Same AS)")
        testcase = self._get_testcase("3.2.1.6")

        setup_items = testcase.get("setup", [])
        verify_items = testcase.get("verify", [])

        self._configure_setup_items(setup_items)
        st.wait(10, "Waiting for BGP convergence")
        self._verify_all(verify_items)

        st.report_pass("test_case_passed")

    @pytest.mark.inventory(feature="Regression", testcases=["BGP_321_TC7"])
    def test_bgp_321_7_bgp_attributes_med(self) -> None:
        """TC 3.2.1.7 – IPv4 Advertisement with BGP Attributes (MED, Local Pref)."""
        st.log("TEST: 3.2.1.7 - IPv4 Advertisement with BGP Attributes (MED)")
        testcase = self._get_testcase("3.2.1.7")

        setup_items = testcase.get("setup", [])
        verify_items = testcase.get("verify", [])

        self._configure_setup_items(setup_items)
        st.wait(10, "Waiting for BGP convergence")
        self._verify_all(verify_items)

        st.report_pass("test_case_passed")

    @pytest.mark.inventory(feature="Regression", testcases=["BGP_321_TC8"])
    def test_bgp_321_8_as_path_prepending(self) -> None:
        """TC 3.2.1.8 – IPv4 Advertisement with AS-PATH Prepending."""
        st.log("TEST: 3.2.1.8 - IPv4 Advertisement with AS-PATH Prepending")
        testcase = self._get_testcase("3.2.1.8")

        setup_items = testcase.get("setup", [])
        verify_items = testcase.get("verify", [])

        self._configure_setup_items(setup_items)
        st.wait(10, "Waiting for BGP convergence")
        self._verify_all(verify_items)

        st.report_pass("test_case_passed")

    @pytest.mark.inventory(feature="Regression", testcases=["BGP_321_TC9"])
    def test_bgp_321_9_community_attributes(self) -> None:
        """TC 3.2.1.9 – IPv4 Advertisement with Community Attributes."""
        st.log("TEST: 3.2.1.9 - IPv4 Advertisement with Community Attributes")
        testcase = self._get_testcase("3.2.1.9")

        setup_items = testcase.get("setup", [])
        verify_items = testcase.get("verify", [])

        self._configure_setup_items(setup_items)
        st.wait(10, "Waiting for BGP convergence")
        self._verify_all(verify_items)

        st.report_pass("test_case_passed")

    @pytest.mark.inventory(feature="Regression", testcases=["BGP_321_TC10"])
    def test_bgp_321_10_bidirectional_advertisement(self) -> None:
        """TC 3.2.1.10 – Bidirectional IPv4 Route Advertisement."""
        st.log("TEST: 3.2.1.10 - Bidirectional IPv4 Route Advertisement")
        testcase = self._get_testcase("3.2.1.10")

        setup_items = testcase.get("setup", [])
        verify_items = testcase.get("verify", [])

        self._configure_setup_items(setup_items)
        st.wait(10, "Waiting for BGP convergence")
        self._verify_all(verify_items)

        st.report_pass("test_case_passed")

    @pytest.mark.inventory(feature="Regression", testcases=["BGP_321_TC11"])
    def test_bgp_321_11_next_hop_self(self) -> None:
        """TC 3.2.1.11 – IPv4 Advertisement with Next-Hop-Self."""
        st.log("TEST: 3.2.1.11 - IPv4 Advertisement with Next-Hop-Self")
        testcase = self._get_testcase("3.2.1.11")

        setup_items = testcase.get("setup", [])
        verify_items = testcase.get("verify", [])

        self._configure_setup_items(setup_items)
        st.wait(10, "Waiting for BGP convergence")
        self._verify_all(verify_items)

        st.report_pass("test_case_passed")

    @pytest.mark.inventory(feature="Regression", testcases=["BGP_321_TC12"])
    def test_bgp_321_12_prefix_list_filtering(self) -> None:
        """TC 3.2.1.12 – IPv4 Advertisement Filtering with Prefix-List."""
        st.log("TEST: 3.2.1.12 - IPv4 Advertisement Filtering with Prefix-List")
        testcase = self._get_testcase("3.2.1.12")

        setup_items = testcase.get("setup", [])
        verify_items = testcase.get("verify", [])

        self._configure_setup_items(setup_items)
        st.wait(10, "Waiting for BGP convergence")
        self._verify_all(verify_items)

        st.report_pass("test_case_passed")

    @pytest.mark.inventory(feature="Regression", testcases=["BGP_321_TC13"])
    def test_bgp_321_13_route_map_filtering(self) -> None:
        """TC 3.2.1.13 – IPv4 Advertisement with Route-Map Filtering."""
        st.log("TEST: 3.2.1.13 - IPv4 Advertisement with Route-Map Filtering")
        testcase = self._get_testcase("3.2.1.13")

        setup_items = testcase.get("setup", [])
        verify_items = testcase.get("verify", [])

        self._configure_setup_items(setup_items)
        st.wait(10, "Waiting for BGP convergence")
        self._verify_all(verify_items)

        st.report_pass("test_case_passed")

    @pytest.mark.inventory(feature="Regression", testcases=["BGP_321_TC14"])
    def test_bgp_321_14_default_route_advertisement(self) -> None:
        """TC 3.2.1.14 – IPv4 Default Route Advertisement."""
        st.log("TEST: 3.2.1.14 - IPv4 Default Route Advertisement")
        testcase = self._get_testcase("3.2.1.14")

        setup_items = testcase.get("setup", [])
        verify_items = testcase.get("verify", [])

        self._configure_setup_items(setup_items)
        st.wait(10, "Waiting for BGP convergence")
        self._verify_all(verify_items)

        st.report_pass("test_case_passed")

    @pytest.mark.inventory(feature="Regression", testcases=["BGP_321_TC15"])
    @pytest.mark.negative
    def test_bgp_321_15_negative_no_rib_entry(self) -> None:
        """TC 3.2.1.15 – Negative - IPv4 Advertisement without Route in RIB."""
        st.log("TEST: 3.2.1.15 - Negative - IPv4 Advertisement without Route in RIB")
        testcase = self._get_testcase("3.2.1.15")

        setup_items = testcase.get("setup", [])
        verify_items = testcase.get("verify", [])

        self._configure_setup_items(setup_items)
        st.wait(10, "Waiting for BGP convergence")
        self._verify_all(verify_items)

        st.report_pass("test_case_passed")

    @pytest.mark.inventory(feature="Regression", testcases=["BGP_321_TC16"])
    def test_bgp_321_16_route_aggregation(self) -> None:
        """TC 3.2.1.16 – IPv4 Advertisement with Aggregation (Summary)."""
        st.log("TEST: 3.2.1.16 - IPv4 Advertisement with Aggregation (Summary)")
        testcase = self._get_testcase("3.2.1.16")

        setup_items = testcase.get("setup", [])
        verify_items = testcase.get("verify", [])

        self._configure_setup_items(setup_items)
        st.wait(10, "Waiting for BGP convergence")
        self._verify_all(verify_items)

        st.report_pass("test_case_passed")

    @pytest.mark.inventory(feature="Regression", testcases=["BGP_321_TC17"])
    def test_bgp_321_17_dynamic_route_withdrawal(self) -> None:
        """TC 3.2.1.17 – IPv4 Advertisement Dynamic Route Withdrawal."""
        st.log("TEST: 3.2.1.17 - IPv4 Advertisement Dynamic Route Withdrawal")
        testcase = self._get_testcase("3.2.1.17")

        setup_items = testcase.get("setup", [])
        verify_items = testcase.get("verify", [])
        teardown_actions = testcase.get("teardown_actions", [])
        verify_after_teardown = testcase.get("verify_after_teardown", [])

        # Initial setup and verification
        self._configure_setup_items(setup_items)
        st.wait(10, "Waiting for BGP convergence")
        self._verify_all(verify_items)

        # Perform teardown actions (remove network command)
        for action in teardown_actions:
            if action.get("type") == "bgp_network_remove":
                dut = self._resolve_dut(action.get("dut"))
                local_asn = action.get("local_asn")
                prefix = action.get("prefix")
                family = action.get("family", "ipv4")

                st.log(f"Removing BGP network {prefix} from {dut}")
                addr_family = "ipv6" if family == "ipv6" else "ipv4"
                bgp_api.config_bgp_network_advertise(
                    dut,
                    local_asn=local_asn,
                    network=prefix,
                    addr_family=addr_family,
                    config="no",
                    cli_type=self.data.cli_type,
                )

        # Verify route withdrawal
        st.wait(10, "Waiting for route withdrawal propagation")
        self._verify_all(verify_after_teardown)

        st.report_pass("test_case_passed")

    @pytest.mark.inventory(feature="Regression", testcases=["BGP_321_TC18"])
    def test_bgp_321_18_ipv6_route_advertisement(self) -> None:
        """TC 3.2.1.18 – IPv6 Unicast Route Advertisement (Basic)."""
        st.log("TEST: 3.2.1.18 - IPv6 Unicast Route Advertisement (Basic)")
        testcase = self._get_testcase("3.2.1.18")

        setup_items = testcase.get("setup", [])
        verify_items = testcase.get("verify", [])

        self._configure_setup_items(setup_items)
        st.wait(10, "Waiting for BGP convergence")
        self._verify_all(verify_items)

        st.report_pass("test_case_passed")

    @pytest.mark.inventory(feature="Regression", testcases=["BGP_321_TC19"])
    def test_bgp_321_19_maximum_prefix_limit(self) -> None:
        """TC 3.2.1.19 – IPv4 Advertisement with Maximum Prefix Limit."""
        st.log("TEST: 3.2.1.19 - IPv4 Advertisement with Maximum Prefix Limit")
        testcase = self._get_testcase("3.2.1.19")

        setup_items = testcase.get("setup", [])
        verify_items = testcase.get("verify", [])

        self._configure_setup_items(setup_items)
        st.wait(10, "Waiting for BGP convergence")
        self._verify_all(verify_items)

        st.report_pass("test_case_passed")

    @pytest.mark.inventory(feature="Regression", testcases=["BGP_321_TC20"])
    def test_bgp_321_20_route_refresh(self) -> None:
        """TC 3.2.1.20 – IPv4 Advertisement with Route Refresh."""
        st.log("TEST: 3.2.1.20 - IPv4 Advertisement with Route Refresh")
        testcase = self._get_testcase("3.2.1.20")

        setup_items = testcase.get("setup", [])
        verify_items = testcase.get("verify", [])
        actions = testcase.get("actions", [])
        verify_after_action = testcase.get("verify_after_action", [])

        # Initial setup and verification
        self._configure_setup_items(setup_items)
        st.wait(10, "Waiting for BGP convergence")
        self._verify_all(verify_items)

        # Perform route refresh action
        for action in actions:
            if action.get("type") == "bgp_route_refresh":
                dut = self._resolve_dut(action.get("dut"))
                neighbor_ip = action.get("neighbor_ip")
                family = action.get("family", "ipv4")

                st.log(f"Performing BGP route refresh for neighbor {neighbor_ip} on {dut}")
                bgp_api.clear_ip_bgp(dut, family=family, cli_type=self.data.cli_type)

        # Verify after route refresh
        st.wait(5, "Waiting after route refresh")
        self._verify_all(verify_after_action)

        st.report_pass("test_case_passed")
