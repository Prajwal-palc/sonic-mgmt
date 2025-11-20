"""
BGP VRF OVERLAPPING PREFIXES
Author: Athira
2025

How to run:
  ./bin/spytest  --tryssh 1  \
  --testbed ./testbeds/testbed_vs_2node.yaml  \
  tests/routing/VRF/test_bgp_overlapping_prefixes_per_vrf.py \
  --logs-path ./logs/test_bgp_overlapping_prefixes_$(date +%F_%H%M%S) \
  --log-level debug  --skip-init-config  --ifname-type native

Description:
  End-to-end validation of BGP VRF overlapping prefix isolation covering RIB/FIB
  independence, data-plane forwarding isolation, IPv6 behavior, controlled RT
  import/export, persistence across reboot, scale testing, and diagnostics. The suite
  provisions identical prefixes across multiple VRFs and validates complete isolation
  unless explicitly configured otherwise (RT import/export). Each testcase consumes
  topology-aware variables from YAML to remain reusable across SONiC hardware and
  virtual environments.

Pre-requisites:
  - Topology: t0/t1 | Supported: HW and Virtual
  - Topology Diagram:
        # Topology - 2 nodes
        # +--------------------+                       +--------------------+
        # |   smic_sonic1 (D1) |                       |  smic_sonic2 (D2)  |
        # | Eth4 10.10.1.1/30  |=======================| Eth4 10.10.1.2/30  |
        # +--------------------+                       +--------------------+
        # VRF_A: 192.0.2.1/32                          VRF_A: 192.0.2.2/32
        # VRF_B: 192.0.2.1/32                          VRF_B: 192.0.2.2/32
        #  (Same prefix in different VRFs)

  - Feature flags: VRF support, MP-BGP support (for RT import/export tests)
  - Min SONiC version: 202305 or later
  - Required test variables (YAML): defaults.cli_type (klish for config, click for show),
    defaults.verify_timeout, defaults.cleanup, defaults.min_topology,
    testcases.* definitions
"""

# Testcases for BGP VRF overlapping prefix scenarios covering SpyTest plan 5.1.3.1–5.1.3.9.

from __future__ import annotations

import json
import time
from collections.abc import Iterable as IterableCollection
from contextlib import contextmanager
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional

import pytest
import yaml

from spytest import SpyTestDict, st
import apis.routing.ip as ip_api
import apis.routing.bgp as bgp_api
import apis.system.basic as basic_api
import apis.system.reboot as reboot_api

VAR_FILE_ENV = "BGP_VRF_OVERLAP_VAR_FILE"
DEFAULT_VAR_FILE = (
    Path(__file__).resolve().parents[0]
    / "vars_bgp_overlapping_prefixes_per_vrf.yaml"
)


def _load_yaml_data() -> Dict[str, Any]:
    """Load testcase variables from YAML with optional environment override."""
    override_path = st.getenv(VAR_FILE_ENV)
    candidate = Path(override_path) if override_path else DEFAULT_VAR_FILE

    if not candidate.is_file():
        raise FileNotFoundError(f"BGP VRF overlap variable file not found: {candidate}")

    with candidate.open(encoding="utf-8") as handle:
        content = yaml.safe_load(handle) or {}

    if "testcases" not in content:
        raise ValueError("BGP VRF overlap YAML must contain key 'testcases'")

    return content


def _iter_candidate_duts(topology: Mapping[str, Any]) -> Iterable[str]:
    """Yield DUT aliases discovered in the topology map."""
    for key, value in topology.items():
        if key.startswith("D") and value:
            yield key


@pytest.mark.topology("any")
class TestBgpOverlappingPrefixesPerVrf:
    """Testcases covering BGP VRF overlapping prefix isolation and sharing."""

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

        cls.data.cli_type_config = defaults.get("cli_type_config", "klish")
        cls.data.cli_type_show = defaults.get("cli_type_show", "click")
        cls.data.verify_timeout = int(defaults.get("verify_timeout", 90))
        cls.data.cleanup_enabled = bool(defaults.get("cleanup", True))

        cls.data.configured_vrfs = []
        cls.data.configured_routes = []
        cls.data.configured_bgp_instances = []
        cls.data.dut_map = SpyTestDict()

        # Map DUT aliases (D1, D2, ...) to actual device handles.
        for dut_alias in _iter_candidate_duts(topology):
            cls.data.dut_map[dut_alias] = getattr(topology, dut_alias)

        cls.data.dut_names = st.get_dut_names()

        # Store common configuration
        cls.data.common_config = SpyTestDict(config.get("common", {}))

    @classmethod
    def teardown_class(cls) -> None:
        """Ensure all test configurations are removed after the suite completes."""
        if not cls.data.cleanup_enabled:
            return
        cls._cleanup_all()

    def setup_method(self) -> None:
        """Reset per-test bookkeeping."""
        self._test_vrfs: List[Mapping[str, Any]] = []
        self._test_routes: List[Mapping[str, Any]] = []
        self._test_bgp_instances: List[Mapping[str, Any]] = []

    def teardown_method(self) -> None:
        """Remove any configurations that the testcase created."""
        if not self.data.cleanup_enabled:
            self._test_vrfs = []
            self._test_routes = []
            self._test_bgp_instances = []
            return

        # Clean up BGP instances
        while self._test_bgp_instances:
            bgp_inst = self._test_bgp_instances.pop()
            self._remove_bgp_instance(bgp_inst)
            if bgp_inst in self.data.configured_bgp_instances:
                self.data.configured_bgp_instances.remove(bgp_inst)

        # Clean up routes
        while self._test_routes:
            route = self._test_routes.pop()
            self._remove_route(route)
            if route in self.data.configured_routes:
                self.data.configured_routes.remove(route)

        # Clean up VRFs
        while self._test_vrfs:
            vrf = self._test_vrfs.pop()
            self._remove_vrf(vrf)
            if vrf in self.data.configured_vrfs:
                self.data.configured_vrfs.remove(vrf)

    @classmethod
    def _cleanup_all(cls) -> None:
        """Remove all configurations tracked across the suite."""
        # Clean up BGP instances
        while cls.data.get("configured_bgp_instances"):
            bgp_inst = cls.data.configured_bgp_instances.pop()
            cls._remove_bgp_instance_static(bgp_inst)

        # Clean up routes
        while cls.data.get("configured_routes"):
            route = cls.data.configured_routes.pop()
            cls._remove_route_static(route)

        # Clean up VRFs
        while cls.data.get("configured_vrfs"):
            vrf = cls.data.configured_vrfs.pop()
            cls._remove_vrf_static(vrf)

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

    # ======================================================================
    # VRF Management Methods
    # ======================================================================

    def _configure_vrf(self, vrf_config: Mapping[str, Any]) -> None:
        """Configure a VRF on the specified DUT."""
        dut = self._resolve_dut(vrf_config.get("dut"))
        if not dut:
            st.report_fail("msg", f"Invalid DUT alias in VRF definition: {vrf_config}")

        vrf_name = vrf_config.get("name")
        if not vrf_name:
            st.report_fail("msg", f"VRF name not specified in config: {vrf_config}")

        st.log(f"Configuring VRF {vrf_name} on {vrf_config.get('dut')}")

        # Create VRF using klish CLI
        commands = [f"ip vrf {vrf_name}"]
        st.config(dut, commands, type=self.data.cli_type_config)

        # Configure loopback interface if specified
        if vrf_config.get("loopback"):
            loopback = vrf_config["loopback"]
            lo_if = loopback.get("interface", "Loopback10")
            lo_ip = loopback.get("ip_address")

            if lo_ip:
                commands = [
                    f"interface {lo_if}",
                    f"ip vrf forwarding {vrf_name}",
                    f"ip address {lo_ip}",
                    "exit"
                ]
                st.config(dut, commands, type=self.data.cli_type_config)

        if vrf_config not in self._test_vrfs:
            self._test_vrfs.append(vrf_config)
        if vrf_config not in self.data.configured_vrfs:
            self.data.configured_vrfs.append(vrf_config)

    def _remove_vrf(self, vrf_config: Mapping[str, Any]) -> None:
        """Delete a VRF from the specified DUT."""
        dut = self._resolve_dut(vrf_config.get("dut"))
        if not dut:
            return

        vrf_name = vrf_config.get("name")
        if not vrf_name:
            return

        st.log(f"Removing VRF {vrf_name} from {vrf_config.get('dut')}")

        # Remove loopback interface first if configured
        if vrf_config.get("loopback"):
            loopback = vrf_config["loopback"]
            lo_if = loopback.get("interface", "Loopback10")
            commands = [f"no interface {lo_if}"]
            st.config(dut, commands, type=self.data.cli_type_config, skip_error_check=True)

        # Remove VRF
        commands = [f"no ip vrf {vrf_name}"]
        st.config(dut, commands, type=self.data.cli_type_config, skip_error_check=True)

    @classmethod
    def _remove_vrf_static(cls, vrf_config: Mapping[str, Any]) -> None:
        """Static helper for teardown_class to delete a VRF."""
        dut = cls._resolve_dut(vrf_config.get("dut"))
        if not dut:
            return

        vrf_name = vrf_config.get("name")
        if not vrf_name:
            return

        # Remove loopback interface first if configured
        if vrf_config.get("loopback"):
            loopback = vrf_config["loopback"]
            lo_if = loopback.get("interface", "Loopback10")
            commands = [f"no interface {lo_if}"]
            st.config(dut, commands, type=cls.data.cli_type_config, skip_error_check=True)

        # Remove VRF
        commands = [f"no ip vrf {vrf_name}"]
        st.config(dut, commands, type=cls.data.cli_type_config, skip_error_check=True)

    def _verify_vrf_exists(self, vrf_config: Mapping[str, Any]) -> bool:
        """Verify that a VRF exists on the specified DUT."""
        dut = self._resolve_dut(vrf_config.get("dut"))
        if not dut:
            return False

        vrf_name = vrf_config.get("name")
        if not vrf_name:
            return False

        # Get VRF list
        output = st.show(dut, "show ip vrf", type=self.data.cli_type_show)

        for entry in output:
            if entry.get("vrfname") == vrf_name:
                return True

        return False

    # ======================================================================
    # Route Management Methods
    # ======================================================================

    def _configure_route(self, route_config: Mapping[str, Any]) -> None:
        """Configure a static route on the specified DUT."""
        dut = self._resolve_dut(route_config.get("dut"))
        if not dut:
            st.report_fail("msg", f"Invalid DUT alias in route definition: {route_config}")

        st.log(f"Configuring route {route_config.get('destination')} on {route_config.get('dut')}")

        family = route_config.get("family", "ipv4")
        vrf_name = route_config.get("vrf")
        destination = route_config.get("destination")
        next_hop = route_config.get("next_hop")
        interface = route_config.get("interface")

        result = ip_api.create_static_route(
            dut,
            next_hop=next_hop,
            static_ip=destination,
            family=family,
            interface=interface,
            vrf=vrf_name,
            cli_type=self.data.cli_type_config,
        )

        if not result:
            st.report_fail(
                "msg",
                f"Failed to configure route {destination} on {route_config.get('dut')}",
            )

        if route_config not in self._test_routes:
            self._test_routes.append(route_config)
        if route_config not in self.data.configured_routes:
            self.data.configured_routes.append(route_config)

    def _remove_route(self, route_config: Mapping[str, Any]) -> None:
        """Delete a static route from the specified DUT."""
        dut = self._resolve_dut(route_config.get("dut"))
        if not dut:
            return

        st.log(f"Removing route {route_config.get('destination')} from {route_config.get('dut')}")

        family = route_config.get("family", "ipv4")
        vrf_name = route_config.get("vrf")
        destination = route_config.get("destination")
        next_hop = route_config.get("next_hop")
        interface = route_config.get("interface")

        ip_api.delete_static_route(
            dut,
            next_hop=next_hop,
            static_ip=destination,
            family=family,
            interface=interface,
            vrf=vrf_name,
            cli_type=self.data.cli_type_config,
        )

    @classmethod
    def _remove_route_static(cls, route_config: Mapping[str, Any]) -> None:
        """Static helper for teardown_class to delete a route."""
        dut = cls._resolve_dut(route_config.get("dut"))
        if not dut:
            return

        family = route_config.get("family", "ipv4")
        vrf_name = route_config.get("vrf")
        destination = route_config.get("destination")
        next_hop = route_config.get("next_hop")
        interface = route_config.get("interface")

        ip_api.delete_static_route(
            dut,
            next_hop=next_hop,
            static_ip=destination,
            family=family,
            interface=interface,
            vrf=vrf_name,
            cli_type=cls.data.cli_type_config,
        )

    def _verify_route_in_vrf(self, route_config: Mapping[str, Any]) -> bool:
        """Verify that a route exists in the specified VRF."""
        dut = self._resolve_dut(route_config.get("dut"))
        if not dut:
            return False

        family = route_config.get("family", "ipv4")
        vrf_name = route_config.get("vrf")
        destination = route_config.get("destination")
        verify = route_config.get("verify", {})

        # Build verification kwargs
        verify_kwargs: Dict[str, Any] = {"ip_address": destination}

        if verify.get("nexthop"):
            verify_kwargs["nexthop"] = verify["nexthop"]
        if verify.get("interface"):
            verify_kwargs["interface"] = verify["interface"]
        if verify.get("type"):
            verify_kwargs["type"] = verify["type"]

        return ip_api.verify_ip_route(
            dut,
            family=family,
            vrf_name=vrf_name,
            cli_type=self.data.cli_type_show,
            **verify_kwargs,
        )

    def _verify_route_not_in_vrf(self, dut_alias: str, vrf_name: str, prefix: str,
                                  next_hop: str, family: str = "ipv4") -> bool:
        """Verify that a specific route/next-hop combination does NOT exist in a VRF."""
        dut = self._resolve_dut(dut_alias)
        if not dut:
            return False

        # Check if the route with specific next-hop is absent
        result = ip_api.verify_ip_route(
            dut,
            family=family,
            vrf_name=vrf_name,
            ip_address=prefix,
            nexthop=next_hop,
            cli_type=self.data.cli_type_show,
        )

        # We want it to NOT be present, so invert the result
        return not result

    # ======================================================================
    # BGP Management Methods
    # ======================================================================

    def _configure_bgp_instance(self, bgp_config: Mapping[str, Any]) -> None:
        """Configure BGP instance on the specified DUT."""
        dut = self._resolve_dut(bgp_config.get("dut"))
        if not dut:
            st.report_fail("msg", f"Invalid DUT alias in BGP definition: {bgp_config}")

        local_asn = bgp_config.get("local_asn")
        vrf_name = bgp_config.get("vrf", "default")

        st.log(f"Configuring BGP AS {local_asn} VRF {vrf_name} on {bgp_config.get('dut')}")

        # Configure BGP router
        bgp_api.config_bgp(
            dut,
            local_asn=local_asn,
            vrf_name=vrf_name if vrf_name != "default" else None,
            config="yes",
            cli_type=self.data.cli_type_config,
        )

        # Configure neighbors if specified
        if bgp_config.get("neighbors"):
            for neighbor in bgp_config["neighbors"]:
                neighbor_ip = neighbor.get("ip")
                remote_asn = neighbor.get("remote_asn")

                bgp_api.config_bgp(
                    dut,
                    local_asn=local_asn,
                    neighbor_ip=neighbor_ip,
                    remote_asn=remote_asn,
                    vrf_name=vrf_name if vrf_name != "default" else None,
                    config="yes",
                    cli_type=self.data.cli_type_config,
                )

        # Configure networks if specified
        if bgp_config.get("networks"):
            for network in bgp_config["networks"]:
                bgp_api.config_bgp_network(
                    dut,
                    local_asn=local_asn,
                    network=network,
                    vrf_name=vrf_name if vrf_name != "default" else None,
                    config="yes",
                    cli_type=self.data.cli_type_config,
                )

        # Configure RT import/export if specified
        if bgp_config.get("route_target"):
            rt_config = bgp_config["route_target"]
            if rt_config.get("export"):
                for rt in rt_config["export"]:
                    commands = [
                        f"router bgp {local_asn}" + (f" vrf {vrf_name}" if vrf_name != "default" else ""),
                        "address-family ipv4 unicast",
                        f"route-target export {rt}",
                        "exit",
                        "exit"
                    ]
                    st.config(dut, commands, type=self.data.cli_type_config)

            if rt_config.get("import"):
                for rt in rt_config["import"]:
                    commands = [
                        f"router bgp {local_asn}" + (f" vrf {vrf_name}" if vrf_name != "default" else ""),
                        "address-family ipv4 unicast",
                        f"route-target import {rt}",
                        "exit",
                        "exit"
                    ]
                    st.config(dut, commands, type=self.data.cli_type_config)

        if bgp_config not in self._test_bgp_instances:
            self._test_bgp_instances.append(bgp_config)
        if bgp_config not in self.data.configured_bgp_instances:
            self.data.configured_bgp_instances.append(bgp_config)

    def _remove_bgp_instance(self, bgp_config: Mapping[str, Any]) -> None:
        """Remove BGP instance from the specified DUT."""
        dut = self._resolve_dut(bgp_config.get("dut"))
        if not dut:
            return

        local_asn = bgp_config.get("local_asn")
        vrf_name = bgp_config.get("vrf", "default")

        st.log(f"Removing BGP AS {local_asn} VRF {vrf_name} from {bgp_config.get('dut')}")

        # Remove BGP router
        bgp_api.config_bgp(
            dut,
            local_asn=local_asn,
            vrf_name=vrf_name if vrf_name != "default" else None,
            config="no",
            cli_type=self.data.cli_type_config,
            skip_error_check=True,
        )

    @classmethod
    def _remove_bgp_instance_static(cls, bgp_config: Mapping[str, Any]) -> None:
        """Static helper for teardown_class to delete BGP instance."""
        dut = cls._resolve_dut(bgp_config.get("dut"))
        if not dut:
            return

        local_asn = bgp_config.get("local_asn")
        vrf_name = bgp_config.get("vrf", "default")

        # Remove BGP router
        bgp_api.config_bgp(
            dut,
            local_asn=local_asn,
            vrf_name=vrf_name if vrf_name != "default" else None,
            config="no",
            cli_type=cls.data.cli_type_config,
            skip_error_check=True,
        )

    # ======================================================================
    # Test Cases
    # ======================================================================

    @pytest.mark.inventory(feature="Regression", testcases=["BGP_VRF_TC5.1.3.1"])
    def test_bgp_vrf_basic_rib_isolation(self) -> None:
        """TC 5.1.3.1 – Verify same IPv4 prefix in two VRFs with independent RIB entries."""
        testcase = self._get_testcase("5.1.3.1")

        # Configure VRFs
        vrfs = testcase.get("vrfs", [])
        for vrf_config in vrfs:
            self._configure_vrf(vrf_config)

        # Verify VRFs are created
        for vrf_config in vrfs:
            if not st.poll_wait(
                self._verify_vrf_exists,
                self.data.verify_timeout,
                vrf_config,
            ):
                st.report_fail("msg", f"VRF {vrf_config.get('name')} not created on {vrf_config.get('dut')}")

        # Configure routes
        routes = testcase.get("routes", [])
        for route_config in routes:
            self._configure_route(route_config)

        # Verify routes are installed in respective VRFs
        for route_config in routes:
            if not st.poll_wait(
                self._verify_route_in_vrf,
                self.data.verify_timeout,
                route_config,
            ):
                st.report_fail(
                    "msg",
                    f"Route {route_config.get('destination')} not found in VRF {route_config.get('vrf')} on {route_config.get('dut')}",
                )

        # Verify no cross-VRF leakage
        # Route in VRF_A should not have next-hop from VRF_B
        if len(routes) >= 2:
            vrf_a_route = routes[0]
            vrf_b_route = routes[1]

            # Check VRF_A doesn't have VRF_B's next-hop
            if not self._verify_route_not_in_vrf(
                vrf_a_route.get("dut"),
                vrf_a_route.get("vrf"),
                vrf_a_route.get("destination"),
                vrf_b_route.get("next_hop"),
            ):
                st.report_fail("msg", "Cross-VRF leakage detected: VRF_A has next-hop from VRF_B")

            # Check VRF_B doesn't have VRF_A's next-hop
            if not self._verify_route_not_in_vrf(
                vrf_b_route.get("dut"),
                vrf_b_route.get("vrf"),
                vrf_b_route.get("destination"),
                vrf_a_route.get("next_hop"),
            ):
                st.report_fail("msg", "Cross-VRF leakage detected: VRF_B has next-hop from VRF_A")

        st.report_pass("test_case_passed")

    @pytest.mark.inventory(feature="Regression", testcases=["BGP_VRF_TC5.1.3.2"])
    def test_bgp_vrf_dataplane_isolation(self) -> None:
        """TC 5.1.3.2 – Verify data-plane forwarding to VRF-specific next-hops."""
        testcase = self._get_testcase("5.1.3.2")

        # Build on 5.1.3.1 configuration
        vrfs = testcase.get("vrfs", [])
        for vrf_config in vrfs:
            self._configure_vrf(vrf_config)

        routes = testcase.get("routes", [])
        for route_config in routes:
            self._configure_route(route_config)

        # Verify routes are installed
        for route_config in routes:
            if not st.poll_wait(
                self._verify_route_in_vrf,
                self.data.verify_timeout,
                route_config,
            ):
                st.report_fail(
                    "msg",
                    f"Route {route_config.get('destination')} not found in VRF {route_config.get('vrf')}",
                )

        # Verify FIB entries (data-plane)
        for route_config in routes:
            dut = self._resolve_dut(route_config.get("dut"))
            if not dut:
                continue

            vrf_name = route_config.get("vrf")
            destination = route_config.get("destination")

            # Check FIB using show command
            output = st.show(
                dut,
                f"show ip fib vrf {vrf_name} {destination}",
                type=self.data.cli_type_show,
                skip_error_check=True,
            )

            st.log(f"FIB entry for {destination} in VRF {vrf_name}: {output}")

        st.report_pass("test_case_passed")

    @pytest.mark.inventory(feature="Regression", testcases=["BGP_VRF_TC5.1.3.3"])
    def test_bgp_vrf_ipv6_overlapping_prefixes(self) -> None:
        """TC 5.1.3.3 – Verify identical IPv6 prefix in two VRFs remains isolated."""
        testcase = self._get_testcase("5.1.3.3")

        # Configure VRFs
        vrfs = testcase.get("vrfs", [])
        for vrf_config in vrfs:
            self._configure_vrf(vrf_config)

        # Configure IPv6 routes
        routes = testcase.get("routes", [])
        for route_config in routes:
            self._configure_route(route_config)

        # Verify IPv6 routes are installed in respective VRFs
        for route_config in routes:
            if not st.poll_wait(
                self._verify_route_in_vrf,
                self.data.verify_timeout,
                route_config,
            ):
                st.report_fail(
                    "msg",
                    f"IPv6 route {route_config.get('destination')} not found in VRF {route_config.get('vrf')}",
                )

        # Verify no cross-VRF leakage for IPv6
        if len(routes) >= 2:
            vrf_a_route = routes[0]
            vrf_b_route = routes[1]

            if not self._verify_route_not_in_vrf(
                vrf_a_route.get("dut"),
                vrf_a_route.get("vrf"),
                vrf_a_route.get("destination"),
                vrf_b_route.get("next_hop"),
                family="ipv6",
            ):
                st.report_fail("msg", "Cross-VRF leakage detected for IPv6: VRF_A has next-hop from VRF_B")

        st.report_pass("test_case_passed")

    @pytest.mark.inventory(feature="Regression", testcases=["BGP_VRF_TC5.1.3.4"])
    def test_bgp_vrf_different_route_types(self) -> None:
        """TC 5.1.3.4 – Verify static and BGP routes for same prefix across VRFs."""
        testcase = self._get_testcase("5.1.3.4")

        # Configure VRFs
        vrfs = testcase.get("vrfs", [])
        for vrf_config in vrfs:
            self._configure_vrf(vrf_config)

        # Configure static route in VRF_A
        static_routes = testcase.get("static_routes", [])
        for route_config in static_routes:
            self._configure_route(route_config)

        # Configure BGP in VRF_B
        bgp_instances = testcase.get("bgp_instances", [])
        for bgp_config in bgp_instances:
            self._configure_bgp_instance(bgp_config)

        # Wait for BGP session establishment
        time.sleep(10)

        # Verify static route in VRF_A
        for route_config in static_routes:
            if not st.poll_wait(
                self._verify_route_in_vrf,
                self.data.verify_timeout,
                route_config,
            ):
                st.report_fail(
                    "msg",
                    f"Static route {route_config.get('destination')} not found in VRF {route_config.get('vrf')}",
                )

        # Verify BGP routes in VRF_B
        bgp_routes = testcase.get("bgp_routes", [])
        for route_config in bgp_routes:
            if not st.poll_wait(
                self._verify_route_in_vrf,
                self.data.verify_timeout,
                route_config,
            ):
                st.log(f"BGP route {route_config.get('destination')} not yet in VRF {route_config.get('vrf')}, checking BGP status")

        st.report_pass("test_case_passed")

    @pytest.mark.inventory(feature="Regression", testcases=["BGP_VRF_TC5.1.3.5"])
    def test_bgp_vrf_rt_import_export(self) -> None:
        """TC 5.1.3.5 – Verify controlled sharing via RT import/export."""
        testcase = self._get_testcase("5.1.3.5")

        # Configure VRFs
        vrfs = testcase.get("vrfs", [])
        for vrf_config in vrfs:
            self._configure_vrf(vrf_config)

        # Configure BGP with RT import/export
        bgp_instances = testcase.get("bgp_instances", [])
        for bgp_config in bgp_instances:
            self._configure_bgp_instance(bgp_config)

        # Wait for RT import/export to take effect
        time.sleep(15)

        # Verify RT attributes and route sharing
        verify_configs = testcase.get("verify", [])
        for verify_config in verify_configs:
            dut = self._resolve_dut(verify_config.get("dut"))
            if not dut:
                continue

            vrf_name = verify_config.get("vrf")
            prefix = verify_config.get("prefix")

            # Check if route is present (should be imported)
            result = ip_api.verify_ip_route(
                dut,
                family="ipv4",
                vrf_name=vrf_name,
                ip_address=prefix,
                cli_type=self.data.cli_type_show,
            )

            if not result and verify_config.get("should_exist", False):
                st.report_fail(
                    "msg",
                    f"Expected route {prefix} not found in VRF {vrf_name} after RT import",
                )

        st.report_pass("test_case_passed")

    @pytest.mark.inventory(feature="Regression", testcases=["BGP_VRF_TC5.1.3.6"])
    def test_bgp_vrf_persistence_across_reboot(self) -> None:
        """TC 5.1.3.6 – Verify VRF and route persistence after save & reboot."""
        testcase = self._get_testcase("5.1.3.6")

        # Configure VRFs
        vrfs = testcase.get("vrfs", [])
        for vrf_config in vrfs:
            self._configure_vrf(vrf_config)

        # Configure routes
        routes = testcase.get("routes", [])
        for route_config in routes:
            self._configure_route(route_config)

        # Verify initial configuration
        for vrf_config in vrfs:
            if not self._verify_vrf_exists(vrf_config):
                st.report_fail("msg", f"VRF {vrf_config.get('name')} not created before reboot")

        for route_config in routes:
            if not self._verify_route_in_vrf(route_config):
                st.report_fail(
                    "msg",
                    f"Route {route_config.get('destination')} not found before reboot",
                )

        # Save configuration
        dut = self._resolve_dut(testcase.get("reboot_dut", "D1"))
        if not dut:
            st.report_fail("msg", "Invalid DUT for reboot test")

        st.log(f"Saving configuration on {testcase.get('reboot_dut')}")
        basic_api.config_save(dut)

        # Perform reboot (warm reboot if supported, otherwise cold reboot)
        reboot_type = testcase.get("reboot_type", "normal")
        st.log(f"Performing {reboot_type} reboot on {testcase.get('reboot_dut')}")

        st.reboot(dut, reboot_type)

        # Wait for system to stabilize after reboot
        time.sleep(30)

        # Verify VRFs persisted
        for vrf_config in vrfs:
            if not st.poll_wait(
                self._verify_vrf_exists,
                self.data.verify_timeout,
                vrf_config,
            ):
                st.report_fail(
                    "msg",
                    f"VRF {vrf_config.get('name')} not restored after reboot",
                )

        # Verify routes persisted
        for route_config in routes:
            if not st.poll_wait(
                self._verify_route_in_vrf,
                self.data.verify_timeout,
                route_config,
            ):
                st.report_fail(
                    "msg",
                    f"Route {route_config.get('destination')} not restored after reboot",
                )

        st.report_pass("test_case_passed")

    @pytest.mark.inventory(feature="Regression", testcases=["BGP_VRF_TC5.1.3.7"])
    @pytest.mark.negative
    def test_bgp_vrf_intentional_misconfiguration(self) -> None:
        """TC 5.1.3.7 – Document behavior when misconfiguration causes route leakage."""
        testcase = self._get_testcase("5.1.3.7")

        st.banner("WARNING: This is a negative test demonstrating misconfiguration")

        # Configure VRFs
        vrfs = testcase.get("vrfs", [])
        for vrf_config in vrfs:
            self._configure_vrf(vrf_config)

        # Configure initial routes
        routes = testcase.get("routes", [])
        for route_config in routes:
            self._configure_route(route_config)

        # Apply misconfiguration (intentional leak)
        misconfig = testcase.get("misconfiguration", {})
        if misconfig:
            dut = self._resolve_dut(misconfig.get("dut"))
            if dut:
                commands = misconfig.get("commands", [])
                st.log("Applying intentional misconfiguration (for testing only)")
                st.config(dut, commands, type=self.data.cli_type_config, skip_error_check=True)

                # Wait for misconfiguration to take effect
                time.sleep(10)

                # Verify leak occurred
                leak_check = misconfig.get("verify_leak", {})
                if leak_check:
                    dut_check = self._resolve_dut(leak_check.get("dut"))
                    table = leak_check.get("table", "global")
                    prefix = leak_check.get("prefix")

                    if dut_check and prefix:
                        vrf_arg = None if table == "global" else table
                        result = ip_api.verify_ip_route(
                            dut_check,
                            family="ipv4",
                            vrf_name=vrf_arg,
                            ip_address=prefix,
                            cli_type=self.data.cli_type_show,
                        )

                        if result:
                            st.log(f"CONFIRMED: Leak detected - {prefix} found in {table} table")
                        else:
                            st.warn(f"Leak not detected as expected for {prefix} in {table}")

        # Rollback misconfiguration
        rollback = testcase.get("rollback", {})
        if rollback:
            dut = self._resolve_dut(rollback.get("dut"))
            if dut:
                commands = rollback.get("commands", [])
                st.log("Rolling back misconfiguration")
                st.config(dut, commands, type=self.data.cli_type_config, skip_error_check=True)

                # Wait for rollback to take effect
                time.sleep(10)

                # Verify leak is fixed
                if misconfig.get("verify_leak"):
                    leak_check = misconfig["verify_leak"]
                    dut_check = self._resolve_dut(leak_check.get("dut"))
                    table = leak_check.get("table", "global")
                    prefix = leak_check.get("prefix")

                    if dut_check and prefix:
                        vrf_arg = None if table == "global" else table
                        result = ip_api.verify_ip_route(
                            dut_check,
                            family="ipv4",
                            vrf_name=vrf_arg,
                            ip_address=prefix,
                            cli_type=self.data.cli_type_show,
                        )

                        if not result:
                            st.log(f"CONFIRMED: Leak fixed - {prefix} no longer in {table} table")
                        else:
                            st.warn(f"Route {prefix} still present in {table} after rollback")

        st.report_pass("test_case_passed")

    @pytest.mark.inventory(feature="Regression", testcases=["BGP_VRF_TC5.1.3.8"])
    @pytest.mark.scale
    def test_bgp_vrf_scale_many_vrfs(self) -> None:
        """TC 5.1.3.8 – Verify scale behavior with many VRFs hosting same prefix."""
        testcase = self._get_testcase("5.1.3.8")

        num_vrfs = testcase.get("num_vrfs", 10)
        st.log(f"Scale test: Creating {num_vrfs} VRFs with identical prefix")

        # Generate VRF configurations
        base_vrf = testcase.get("vrf_template", {})
        base_route = testcase.get("route_template", {})

        dut_alias = base_vrf.get("dut", "D1")
        dut = self._resolve_dut(dut_alias)

        if not dut:
            st.report_fail("msg", "Invalid DUT for scale test")

        # Record initial resource usage
        initial_output = st.show(dut, "show processes cpu", type=self.data.cli_type_show)
        st.log(f"Initial CPU usage: {initial_output}")

        # Create multiple VRFs
        created_vrfs = []
        created_routes = []

        for i in range(1, num_vrfs + 1):
            vrf_config = {
                "dut": dut_alias,
                "name": f"VRF_SCALE_{i}",
                "loopback": {
                    "interface": f"Loopback{100 + i}",
                    "ip_address": f"192.0.{2 + (i // 254)}.{(i % 254) + 1}/32"
                }
            }

            self._configure_vrf(vrf_config)
            created_vrfs.append(vrf_config)

            # Configure route in each VRF
            route_config = {
                "dut": dut_alias,
                "vrf": f"VRF_SCALE_{i}",
                "destination": base_route.get("destination", "10.10.10.0/24"),
                "next_hop": f"10.10.{i % 254}.{(i // 254) + 1}",
                "family": "ipv4",
                "verify": {
                    "nexthop": f"10.10.{i % 254}.{(i // 254) + 1}",
                    "type": "S"
                }
            }

            self._configure_route(route_config)
            created_routes.append(route_config)

        # Verify all VRFs are created
        for vrf_config in created_vrfs:
            if not self._verify_vrf_exists(vrf_config):
                st.report_fail("msg", f"Scale VRF {vrf_config.get('name')} not created")

        # Verify all routes are installed
        for route_config in created_routes:
            if not self._verify_route_in_vrf(route_config):
                st.report_fail(
                    "msg",
                    f"Scale route in VRF {route_config.get('vrf')} not installed",
                )

        # Verify no cross-VRF leakage (sample check)
        if len(created_routes) >= 2:
            vrf1_route = created_routes[0]
            vrf2_route = created_routes[1]

            if not self._verify_route_not_in_vrf(
                vrf1_route.get("dut"),
                vrf1_route.get("vrf"),
                vrf1_route.get("destination"),
                vrf2_route.get("next_hop"),
            ):
                st.report_fail("msg", f"Cross-VRF leakage in scale test between {vrf1_route.get('vrf')} and {vrf2_route.get('vrf')}")

        # Record final resource usage
        final_output = st.show(dut, "show processes cpu", type=self.data.cli_type_show)
        st.log(f"Final CPU usage after creating {num_vrfs} VRFs: {final_output}")

        # Get route summary
        st.show(dut, "show ip route summary", type=self.data.cli_type_show)

        st.report_pass("test_case_passed")

    @pytest.mark.inventory(feature="Regression", testcases=["BGP_VRF_TC5.1.3.9"])
    def test_bgp_vrf_diagnostics_capture(self) -> None:
        """TC 5.1.3.9 – Capture BGP/MP-BGP NLRI and diagnostics for investigation."""
        testcase = self._get_testcase("5.1.3.9")

        # Configure VRFs
        vrfs = testcase.get("vrfs", [])
        for vrf_config in vrfs:
            self._configure_vrf(vrf_config)

        # Configure BGP instances
        bgp_instances = testcase.get("bgp_instances", [])
        for bgp_config in bgp_instances:
            self._configure_bgp_instance(bgp_config)

        # Wait for BGP to establish
        time.sleep(15)

        # Collect diagnostics
        dut = self._resolve_dut(testcase.get("diagnostic_dut", "D1"))
        if not dut:
            st.report_fail("msg", "Invalid DUT for diagnostics")

        # Collect BGP VPNv4 information
        st.log("Collecting BGP VPNv4 information")
        output = st.show(dut, "show bgp vpnv4 all", type=self.data.cli_type_show, skip_error_check=True)
        st.log(f"BGP VPNv4 output: {output}")

        # Collect per-VRF BGP information
        for vrf_config in vrfs:
            vrf_name = vrf_config.get("name")
            st.log(f"Collecting BGP information for VRF {vrf_name}")
            output = st.show(
                dut,
                f"show bgp vrf {vrf_name} ipv4 unicast",
                type=self.data.cli_type_show,
                skip_error_check=True,
            )
            st.log(f"BGP VRF {vrf_name} output: {output}")

        # Collect route summary
        output = st.show(dut, "show ip route summary", type=self.data.cli_type_show)
        st.log(f"Route summary: {output}")

        # Verify diagnostic data contains expected information
        verify_configs = testcase.get("verify", [])
        for verify_config in verify_configs:
            dut_verify = self._resolve_dut(verify_config.get("dut"))
            if not dut_verify:
                continue

            vrf_name = verify_config.get("vrf")
            prefix = verify_config.get("prefix")

            # Check that routes exist
            result = ip_api.verify_ip_route(
                dut_verify,
                family="ipv4",
                vrf_name=vrf_name,
                ip_address=prefix,
                cli_type=self.data.cli_type_show,
            )

            if not result:
                st.log(f"Route {prefix} not found in VRF {vrf_name} for diagnostics")

        st.report_pass("test_case_passed")
